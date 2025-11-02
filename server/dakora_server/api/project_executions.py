"""API endpoints for prompt execution and history"""

from typing import Dict, Any
from uuid import UUID, uuid4
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, delete, desc, func, update
from sqlalchemy.engine import Engine

from dakora_server.auth import get_auth_context, validate_project_access, get_project_vault
from dakora_server.core.database import (
    get_engine,
    get_connection,
    prompt_executions_table,
    traces_table,
    template_traces_table,
)
from dakora_server.core.llm.registry import ProviderRegistry
from dakora_server.core.llm.quota import QuotaService
from dakora_server.core.renderer import Renderer
from dakora_server.core.vault import Vault
from dakora_server.api.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    ExecutionMetrics,
    ModelsResponse,
    ModelInfo,
    ExecutionsResponse,
    ExecutionRecord,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/api/projects/{project_id}/prompts/{prompt_id}/execute")
async def execute_prompt(
    prompt_id: str,
    request: ExecuteRequest,
    project_id: UUID = Depends(validate_project_access),
    auth_context = Depends(get_auth_context),
    vault: Vault = Depends(get_project_vault),
    engine: Engine = Depends(get_engine),
) -> ExecuteResponse:
    """
    Execute a prompt against an LLM provider.

    Checks quota, renders prompt, executes, stores result, and consumes quota.
    """
    # Get workspace_id from project
    from dakora_server.core.database import projects_table

    with get_connection(engine) as conn:
        project_result = conn.execute(
            select(projects_table).where(projects_table.c.id == project_id)
        )
        project_row = project_result.fetchone()
        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")
        workspace_id = str(project_row.workspace_id)

    # Check quota
    quota_service = QuotaService(engine)
    if not await quota_service.check_quota(workspace_id):
        raise HTTPException(status_code=429, detail="Quota exceeded for this month")

    # Load template using PromptManager for version support
    from dakora_server.core.prompt_manager import PromptManager
    try:
        prompt_manager = PromptManager(vault.registry, engine, project_id)

        # Load specific version if provided, otherwise load latest
        if request.version is not None:
            template_spec = prompt_manager.get_version_content(prompt_id, request.version)
        else:
            template_spec = prompt_manager.load(prompt_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {str(e)}")

    # Render template with inputs
    try:
        renderer = Renderer(engine=engine, project_id=project_id)
        rendered_prompt = renderer.render(template_spec.template, request.inputs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to render prompt: {str(e)}")

    # Validate model and provider are provided
    if not request.model:
        raise HTTPException(status_code=400, detail="model is required")
    if not request.provider:
        raise HTTPException(status_code=400, detail="provider is required")

    # Get provider and execute
    provider_registry = ProviderRegistry()
    try:
        provider = provider_registry.get_provider_by_name(workspace_id, request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    model = request.model

    execution_status = "success"
    output_text = None
    error_message = None
    execution_result = None
    trace_id: str | None = None

    try:
        execution_result = await provider.execute(
            prompt=rendered_prompt,
            model=model,
        )
        output_text = execution_result.content
    except Exception as e:
        execution_status = "error"
        error_message = str(e)

    # Store execution record
    execution_id = None
    with get_connection(engine) as conn:
        trace_value: str | None = str(uuid4()) if execution_status == "success" else None
        trace_id = trace_value
        result = conn.execute(
            insert(prompt_executions_table).values(
                project_id=project_id,
                prompt_id=prompt_id,
                version=template_spec.version,
                trace_id=trace_value,
                inputs_json=request.inputs,
                model=model,
                provider=execution_result.provider if execution_result else request.provider,
                output_text=output_text,
                error_message=error_message,
                status=execution_status,
                tokens_input=execution_result.tokens_input if execution_result else None,
                tokens_output=execution_result.tokens_output if execution_result else None,
                tokens_total=execution_result.tokens_total if execution_result else None,
                cost_usd=execution_result.cost_usd if execution_result else None,
                latency_ms=execution_result.latency_ms if execution_result else None,
                user_id=auth_context.user_id,
                workspace_id=UUID(workspace_id),
            ).returning(prompt_executions_table.c.id, prompt_executions_table.c.created_at)
        )
        row = result.fetchone()
        execution_id = str(row[0])
        created_at_dt = row[1]
        created_at = (
            created_at_dt.isoformat()
            if isinstance(created_at_dt, datetime)
            else datetime.utcnow().isoformat()
        )

        if execution_status == "success" and execution_result and trace_value:
            try:
                user_id = getattr(auth_context, "user_id", None)
                session_id = f"manual:{str(uuid4())}"

                inputs_json_str = json.dumps(request.inputs or {}, default=str)

                conn.execute(
                    insert(traces_table).values(
                        project_id=project_id,
                        trace_id=trace_value,
                        session_id=session_id,
                        source="dakora-studio",
                        agent_id=None,
                        conversation_history=[
                            {"role": "user", "content": rendered_prompt},
                            {"role": "assistant", "content": execution_result.content},
                        ],
                        metadata={
                            "prompt_id": prompt_id,
                            "version": template_spec.version,
                            "execution_id": execution_id,
                            "user_id": user_id,
                        },
                        provider=execution_result.provider,
                        model=execution_result.model,
                        tokens_in=execution_result.tokens_input,
                        tokens_out=execution_result.tokens_output,
                        latency_ms=execution_result.latency_ms,
                        cost_usd=float(execution_result.cost_usd)
                        if execution_result.cost_usd is not None
                        else None,
                        created_at=created_at_dt,
                        prompt_id=prompt_id,
                        version=template_spec.version,
                        inputs_json=inputs_json_str,
                        output_text=execution_result.content,
                        cost=float(execution_result.cost_usd)
                        if execution_result.cost_usd is not None
                        else None,
                    )
                )

                conn.execute(
                    insert(template_traces_table).values(
                        trace_id=trace_value,
                        prompt_id=prompt_id,
                        source="dakora-studio",
                        version=template_spec.version,
                        inputs_json=request.inputs,
                        position=0,
                    )
                )

                trace_id = trace_value
            except Exception as trace_error:  # pragma: no cover
                logger.warning(
                    "Failed to log manual execution trace for prompt %s: %s",
                    prompt_id,
                    trace_error,
                    exc_info=True,
                )
                trace_id = None
                conn.execute(
                    update(prompt_executions_table)
                    .where(prompt_executions_table.c.id == UUID(execution_id))
                    .values(trace_id=None)
                )

        # Cleanup: keep only 20 most recent executions per prompt
        # Count total executions for this prompt
        count_result = conn.execute(
            select(func.count()).select_from(prompt_executions_table).where(
                prompt_executions_table.c.project_id == project_id,
                prompt_executions_table.c.prompt_id == prompt_id,
            )
        )
        total_count = count_result.scalar()

        if total_count > 20:
            # Delete oldest executions beyond the 20 limit
            executions_to_delete = total_count - 20

            # Get IDs of oldest executions to delete
            oldest_executions = conn.execute(
                select(prompt_executions_table.c.id)
                .where(
                    prompt_executions_table.c.project_id == project_id,
                    prompt_executions_table.c.prompt_id == prompt_id,
                )
                .order_by(prompt_executions_table.c.created_at.asc())
                .limit(executions_to_delete)
            )
            ids_to_delete = [row[0] for row in oldest_executions.fetchall()]

            if ids_to_delete:
                conn.execute(
                    delete(prompt_executions_table).where(
                        prompt_executions_table.c.id.in_(ids_to_delete)
                    )
                )

    # Consume quota if execution was successful
    if execution_status == "success" and execution_result:
        await quota_service.consume_quota(workspace_id, execution_result.tokens_total)

    # Return error if execution failed
    if execution_status == "error":
        trace_id = None
        raise HTTPException(status_code=500, detail=error_message)

    # Return success response
    return ExecuteResponse(
        execution_id=execution_id,
        trace_id=trace_id,
        content=execution_result.content,
        metrics=ExecutionMetrics(
            tokens_input=execution_result.tokens_input,
            tokens_output=execution_result.tokens_output,
            tokens_total=execution_result.tokens_total,
            cost_usd=execution_result.cost_usd,
            latency_ms=execution_result.latency_ms,
        ),
        model=execution_result.model,
        provider=execution_result.provider,
        created_at=created_at,
    )


@router.get("/api/projects/{project_id}/models")
async def get_available_models(
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> ModelsResponse:
    """
    Get available models for the workspace.
    """
    # Get workspace_id from project
    from dakora_server.core.database import projects_table

    with get_connection(engine) as conn:
        project_result = conn.execute(
            select(projects_table).where(projects_table.c.id == project_id)
        )
        project_row = project_result.fetchone()
        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")
        workspace_id = str(project_row.workspace_id)

    # Get all available models from all configured providers
    provider_registry = ProviderRegistry()
    models = provider_registry.get_all_models(workspace_id)

    return ModelsResponse(
        models=[
            ModelInfo(
                id=model.id,
                name=model.name,
                provider=model.provider,
                input_cost_per_1k=model.input_cost_per_1k,
                output_cost_per_1k=model.output_cost_per_1k,
                max_tokens=model.max_tokens,
            )
            for model in models
        ],
        default_model=None,  # No default - user must select
    )


@router.get("/api/projects/{project_id}/prompts/{prompt_id}/executions")
async def get_execution_history(
    prompt_id: str,
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> ExecutionsResponse:
    """
    Get execution history for a prompt.
    """
    # Query executions
    with get_connection(engine) as conn:
        result = conn.execute(
            select(prompt_executions_table)
            .where(
                prompt_executions_table.c.project_id == project_id,
                prompt_executions_table.c.prompt_id == prompt_id,
            )
            .order_by(desc(prompt_executions_table.c.created_at))
            .limit(20)
        )
        rows = result.fetchall()

    executions = []
    for row in rows:
        metrics = None
        if row.tokens_total is not None:
            metrics = ExecutionMetrics(
                tokens_input=row.tokens_input or 0,
                tokens_output=row.tokens_output or 0,
                tokens_total=row.tokens_total or 0,
                cost_usd=float(row.cost_usd) if row.cost_usd else 0.0,
                latency_ms=row.latency_ms or 0,
            )

        executions.append(
            ExecutionRecord(
                execution_id=str(row.id),
                prompt_id=row.prompt_id,
                version=row.version,
                trace_id=row.trace_id,
                inputs=row.inputs_json,
                model=row.model,
                provider=row.provider,
                output_text=row.output_text,
                error_message=row.error_message,
                status=row.status,
                metrics=metrics,
                created_at=row.created_at.isoformat(),
            )
        )

    return ExecutionsResponse(
        executions=executions,
        total=len(executions),
    )
