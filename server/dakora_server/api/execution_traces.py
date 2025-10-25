"""API endpoints for trace-based execution logging

This module provides telemetry/observability endpoints for receiving and querying
execution traces from Microsoft Agent Framework middleware and other observability sources.
"""

from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, and_, func, desc
from sqlalchemy.engine import Engine

from dakora_server.auth import validate_project_access
from dakora_server.core.database import (
    get_engine,
    get_connection,
    traces_table,
    template_traces_table,
)
from dakora_server.core.token_pricing import get_pricing_service
from dakora_server.api.schemas import (
    ExecutionCreate,
    ExecutionResponse,
)

router = APIRouter()


@router.post("/api/projects/{project_id}/executions")
async def create_execution(
    project_id: UUID,
    request: ExecutionCreate,
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> ExecutionResponse:
    """
    Create a new execution log with trace-based observability.
    
    This endpoint supports:
    - Observability-only mode (no template linkage)
    - Template linkage via template_usages array
    - Full conversation history storage
    - Session and agent tracking
    """
    with get_connection(engine) as conn:
        # Insert into logs table
        conn.execute(
            insert(traces_table)
            .values(
                project_id=project_id,
                trace_id=request.trace_id,
                parent_trace_id=request.parent_trace_id,
                session_id=request.session_id,
                agent_id=request.agent_id,
                conversation_history=request.conversation_history,
                metadata=request.metadata,
                provider=request.provider,
                model=request.model,
                tokens_in=request.tokens_in,
                tokens_out=request.tokens_out,
                cost_usd=request.cost_usd,
                latency_ms=request.latency_ms,
            )
        )

        # Link to templates if provided
        if request.template_usages:
            for idx, template_usage in enumerate(request.template_usages):
                conn.execute(
                    insert(template_traces_table).values(
                        trace_id=request.trace_id,
                        prompt_id=template_usage.prompt_id,
                        version=template_usage.version,
                        inputs_json=template_usage.inputs,
                        position=idx,
                    )
                )

    return ExecutionResponse(
        trace_id=request.trace_id,
        status="logged",
    )


@router.get("/api/projects/{project_id}/executions")
async def list_executions(
    project_id: UUID,
    session_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    prompt_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> List[dict[str, Any]]:
    """
    List execution logs with optional filters.
    
    Supports filtering by:
    - session_id: All executions in a session
    - agent_id: All executions by an agent
    - prompt_id: All executions using a specific template
    """
    with get_connection(engine) as conn:
        # Build query with filters
        query = (
            select(
                traces_table.c.trace_id,
                traces_table.c.session_id,
                traces_table.c.agent_id,
                traces_table.c.provider,
                traces_table.c.model,
                traces_table.c.tokens_in,
                traces_table.c.tokens_out,
                traces_table.c.cost_usd,
                traces_table.c.latency_ms,
                traces_table.c.created_at,
                traces_table.c.metadata,
            )
            .where(traces_table.c.project_id == project_id)
            .order_by(desc(traces_table.c.created_at))
            .limit(limit)
            .offset(offset)
        )

        # Apply filters
        if session_id:
            query = query.where(traces_table.c.session_id == session_id)
        if agent_id:
            query = query.where(traces_table.c.agent_id == agent_id)
        if prompt_id:
            # Need to join with template_executions to filter by prompt_id
            query = (
                select(
                    traces_table.c.trace_id,
                    traces_table.c.session_id,
                    traces_table.c.agent_id,
                    traces_table.c.provider,
                    traces_table.c.model,
                    traces_table.c.tokens_in,
                    traces_table.c.tokens_out,
                    traces_table.c.cost_usd,
                    traces_table.c.latency_ms,
                    traces_table.c.created_at,
                    traces_table.c.metadata,
                )
                .select_from(
                    traces_table.join(
                        template_traces_table,
                        traces_table.c.trace_id == template_traces_table.c.trace_id,
                    )
                )
                .where(
                    and_(
                        traces_table.c.project_id == project_id,
                        template_traces_table.c.prompt_id == prompt_id,
                    )
                )
                .order_by(desc(traces_table.c.created_at))
                .limit(limit)
                .offset(offset)
            )

        result = conn.execute(query)
        rows = result.fetchall()

    # Get pricing service for cost calculation
    pricing_service = get_pricing_service()

    executions: List[dict[str, Any]] = []
    for row in rows:
        # Calculate cost on-the-fly using current pricing
        cost_usd = pricing_service.calculate_cost(
            provider=row.provider,
            model=row.model,
            tokens_in=row.tokens_in,
            tokens_out=row.tokens_out,
        )
        
        executions.append(
            {
                "trace_id": row.trace_id,
                "session_id": row.session_id,
                "agent_id": row.agent_id,
                "provider": row.provider,
                "model": row.model,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "cost_usd": cost_usd,  # Calculated on server
                "latency_ms": row.latency_ms,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "metadata": row.metadata,
            }
        )

    return executions


@router.get("/api/projects/{project_id}/executions/{trace_id}")
async def get_execution(
    project_id: UUID,
    trace_id: str,
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """
    Get detailed execution log including conversation history and linked templates.
    """
    with get_connection(engine) as conn:
        # Get main execution log
        log_result = conn.execute(
            select(traces_table).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.trace_id == trace_id,
                )
            )
        )
        log_row = log_result.fetchone()

        if not log_row:
            raise HTTPException(status_code=404, detail="Execution not found")

        # Get linked templates
        template_result = conn.execute(
            select(template_traces_table)
            .where(template_traces_table.c.trace_id == trace_id)
            .order_by(template_traces_table.c.position)
        )
        template_rows = template_result.fetchall()

    templates_used: List[dict[str, Any]] = []
    for template_row in template_rows:
        templates_used.append(
            {
                "prompt_id": template_row.prompt_id,
                "version": template_row.version,
                "inputs": template_row.inputs_json,
                "position": template_row.position,
            }
        )

    return {
        "trace_id": log_row.trace_id,
        "parent_trace_id": log_row.parent_trace_id,
        "session_id": log_row.session_id,
        "agent_id": log_row.agent_id,
        "conversation_history": log_row.conversation_history,
        "metadata": log_row.metadata,
        "provider": log_row.provider,
        "model": log_row.model,
        "tokens_in": log_row.tokens_in,
        "tokens_out": log_row.tokens_out,
        "cost_usd": float(log_row.cost_usd) if log_row.cost_usd else None,  # Historical cost
        "latency_ms": log_row.latency_ms,
        "created_at": log_row.created_at.isoformat() if log_row.created_at else None,
        "templates_used": templates_used,
    }


@router.get("/api/projects/{project_id}/prompts/{prompt_id}/analytics")
async def get_template_analytics(
    project_id: UUID,
    prompt_id: str,
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """
    Get aggregated analytics for a specific template.
    
    Returns:
    - Total executions
    - Total cost
    - Average latency
    - Token usage stats
    """
    with get_connection(engine) as conn:
        # Join logs with template_executions to get stats
        result = conn.execute(
            select(
                func.count(traces_table.c.id).label("total_executions"),
                func.sum(traces_table.c.cost_usd).label("total_cost_usd"),
                func.avg(traces_table.c.latency_ms).label("avg_latency_ms"),
                func.sum(traces_table.c.tokens_in).label("total_tokens_in"),
                func.sum(traces_table.c.tokens_out).label("total_tokens_out"),
            )
            .select_from(
                traces_table.join(
                    template_traces_table,
                    traces_table.c.trace_id == template_traces_table.c.trace_id,
                )
            )
            .where(
                and_(
                    traces_table.c.project_id == project_id,
                    template_traces_table.c.prompt_id == prompt_id,
                )
            )
        )
        row = result.fetchone()

    # The aggregate query may return None if there are no matching rows
    # Guard against that to avoid attribute errors when accessing fields.
    if row is None:
        return {
            "prompt_id": prompt_id,
            "total_executions": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
        }

    return {
        "prompt_id": prompt_id,
        "total_executions": row.total_executions or 0,
        "total_cost_usd": float(row.total_cost_usd) if row.total_cost_usd else 0.0,
        "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0.0,
        "total_tokens_in": row.total_tokens_in or 0,
        "total_tokens_out": row.total_tokens_out or 0,
    }
