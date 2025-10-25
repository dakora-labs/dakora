"""API endpoints for prompt optimization"""

from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, insert, delete, desc, func
from sqlalchemy.engine import Engine

from dakora_server.auth import get_auth_context, validate_project_access, get_project_vault
from dakora_server.core.database import (
    get_engine,
    get_connection,
    optimization_runs_table,
    projects_table,
)
from dakora_server.core.optimizer import OptimizationEngine, OptimizationRequest, OptimizationQuotaService
from dakora_server.core.llm.registry import ProviderRegistry
from dakora_server.core.vault import Vault
from dakora_server.api.schemas import (
    OptimizePromptRequest,
    OptimizePromptResponse,
    OptimizationInsight,
    OptimizationRunRecord,
    OptimizationRunsResponse,
    QuotaInfo,
)

router = APIRouter()


@router.post("/api/projects/{project_id}/prompts/{prompt_id}/optimize")
async def optimize_prompt(
    prompt_id: str,
    request: OptimizePromptRequest,
    project_id: UUID = Depends(validate_project_access),
    auth_context = Depends(get_auth_context),
    vault: Vault = Depends(get_project_vault),
    engine: Engine = Depends(get_engine),
) -> OptimizePromptResponse:
    """
    Optimize a prompt template using AI.

    Checks quota, generates optimized variants, and stores the result.
    """
    # Get workspace_id from project
    with get_connection(engine) as conn:
        project_result = conn.execute(
            select(projects_table).where(projects_table.c.id == project_id)
        )
        project_row = project_result.fetchone()
        if not project_row:
            raise HTTPException(status_code=404, detail="Project not found")
        workspace_id = str(project_row.workspace_id)

    # Check optimization quota
    quota_service = OptimizationQuotaService(engine)
    if not await quota_service.check_quota(workspace_id):
        usage = await quota_service.get_usage(workspace_id)
        raise HTTPException(
            status_code=429,
            detail=f"Optimization quota exceeded. {usage.optimizations_used}/{usage.optimizations_limit} used this month. Upgrade to Pro for more optimizations.",
        )

    # Load template from vault
    try:
        template_spec = vault.get(prompt_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Prompt not found: {str(e)}")

    # Get LLM provider for optimization
    provider_registry = ProviderRegistry()
    try:
        provider = provider_registry.get_provider(workspace_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"No LLM provider configured for this workspace: {str(e)}",
        )

    # Get default model
    models = provider.list_models()
    if not models:
        raise HTTPException(
            status_code=400,
            detail="No models available for optimization",
        )
    model = models[0].id  # Use first available model

    # Create optimization engine
    optimization_engine = OptimizationEngine(provider, model=model)

    # Build optimization request
    opt_request = OptimizationRequest(
        template=template_spec.template,
        test_cases=request.test_cases,
    )

    # Run optimization
    try:
        result = await optimization_engine.optimize(opt_request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(e)}",
        )

    # Store optimization run
    optimization_id = None
    with get_connection(engine) as conn:
        insert_result = conn.execute(
            insert(optimization_runs_table).values(
                project_id=project_id,
                prompt_id=prompt_id,
                version=template_spec.version,
                original_template=template_spec.template,
                optimized_template=result.best_variant.template,
                insights=[
                    {
                        "category": insight.category,
                        "description": insight.description,
                        "impact": insight.impact,
                    }
                    for insight in result.insights
                ],
                token_reduction_pct=result.token_reduction_pct,
                applied=0,  # Not yet applied
                user_id=auth_context.user_id,
                workspace_id=UUID(workspace_id),
            ).returning(optimization_runs_table.c.id, optimization_runs_table.c.created_at)
        )
        row = insert_result.fetchone()
        optimization_id = str(row[0])
        created_at = row[1].isoformat() + 'Z'  # Add Z to indicate UTC

        # Cleanup: keep only 10 most recent optimization runs per prompt
        count_result = conn.execute(
            select(func.count()).select_from(optimization_runs_table).where(
                optimization_runs_table.c.project_id == project_id,
                optimization_runs_table.c.prompt_id == prompt_id,
            )
        )
        total_count = count_result.scalar()

        if total_count > 10:
            # Delete oldest optimization runs beyond the 10 limit
            runs_to_delete = total_count - 10

            # Get IDs of oldest runs to delete
            oldest_runs = conn.execute(
                select(optimization_runs_table.c.id)
                .where(
                    optimization_runs_table.c.project_id == project_id,
                    optimization_runs_table.c.prompt_id == prompt_id,
                )
                .order_by(optimization_runs_table.c.created_at.asc())
                .limit(runs_to_delete)
            )
            ids_to_delete = [row[0] for row in oldest_runs.fetchall()]

            if ids_to_delete:
                conn.execute(
                    delete(optimization_runs_table).where(
                        optimization_runs_table.c.id.in_(ids_to_delete)
                    )
                )

    # Consume quota after successful optimization
    await quota_service.consume_quota(workspace_id)

    # Return response
    return OptimizePromptResponse(
        optimization_id=optimization_id,
        original_template=template_spec.template,
        optimized_template=result.best_variant.template,
        insights=[
            OptimizationInsight(
                category=insight.category,
                description=insight.description,
                impact=insight.impact,
            )
            for insight in result.insights
        ],
        token_reduction_pct=result.token_reduction_pct,
        created_at=created_at,
    )


@router.get("/api/projects/{project_id}/prompts/{prompt_id}/optimization-runs")
async def get_optimization_runs(
    prompt_id: str,
    project_id: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> OptimizationRunsResponse:
    """
    Get optimization run history for a prompt.

    Returns the 10 most recent optimization runs.
    """
    with get_connection(engine) as conn:
        # Get optimization runs
        runs_result = conn.execute(
            select(optimization_runs_table)
            .where(
                optimization_runs_table.c.project_id == project_id,
                optimization_runs_table.c.prompt_id == prompt_id,
            )
            .order_by(desc(optimization_runs_table.c.created_at))
            .limit(10)
        )
        rows = runs_result.fetchall()

        # Count total
        count_result = conn.execute(
            select(func.count()).select_from(optimization_runs_table).where(
                optimization_runs_table.c.project_id == project_id,
                optimization_runs_table.c.prompt_id == prompt_id,
            )
        )
        total = count_result.scalar()

    # Build response
    optimization_runs = []
    for row in rows:
        optimization_runs.append(
            OptimizationRunRecord(
                optimization_id=str(row.id),
                prompt_id=row.prompt_id,
                version=row.version,
                original_template=row.original_template,
                optimized_template=row.optimized_template,
                insights=[
                    OptimizationInsight(**insight) for insight in (row.insights or [])
                ],
                token_reduction_pct=row.token_reduction_pct,
                applied=bool(row.applied),
                created_at=row.created_at.isoformat() + 'Z',  # Add Z to indicate UTC
            )
        )

    return OptimizationRunsResponse(
        optimization_runs=optimization_runs,
        total=total,
    )


@router.get("/api/workspaces/{workspace_id}/quota")
async def get_workspace_quota(
    workspace_id: UUID,
    engine: Engine = Depends(get_engine),
) -> QuotaInfo:
    """
    Get workspace quota information (both tokens and optimizations).
    """
    quota_service = OptimizationQuotaService(engine)
    usage = await quota_service.get_usage(str(workspace_id))

    return QuotaInfo(
        tier=usage.tier,
        optimizations_used=usage.optimizations_used,
        optimizations_limit=usage.optimizations_limit,
        optimizations_remaining=usage.optimizations_remaining,
        usage_percentage=usage.usage_percentage,
        period_start=usage.period_start.isoformat(),
        period_end=usage.period_end.isoformat(),
    )
