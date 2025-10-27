"""API endpoints for trace-based execution logging

This module provides telemetry/observability endpoints for receiving and querying
execution traces from Microsoft Agent Framework middleware and other observability sources.
"""

from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, and_, func, desc, exists, or_
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
    ExecutionListItem,
    ExecutionListResponse,
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
    pricing_service = get_pricing_service()
    calculated_cost: Optional[float] = None

    if (
        request.provider
        and request.model
        and (request.tokens_in is not None or request.tokens_out is not None)
    ):
        try:
            calculated_cost = pricing_service.calculate_cost(
                provider=request.provider,
                model=request.model,
                tokens_in=request.tokens_in or 0,
                tokens_out=request.tokens_out or 0,
            )
        except Exception:
            calculated_cost = None

    cost_value = request.cost_usd if request.cost_usd is not None else calculated_cost

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
                source=request.source,
                conversation_history=request.conversation_history,
                metadata=request.metadata,
                provider=request.provider,
                model=request.model,
                tokens_in=request.tokens_in,
                tokens_out=request.tokens_out,
                cost_usd=cost_value,
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
                        role=template_usage.role,
                        source=template_usage.source,
                        message_index=template_usage.message_index,
                        metadata_json=template_usage.metadata,
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
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    prompt_id: Optional[str] = Query(None),
    has_templates: Optional[bool] = Query(None),
    min_cost: Optional[float] = Query(None, ge=0.0),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: Optional[int] = Query(None, ge=0),
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> ExecutionListResponse:
    """
    List execution logs with optional filters.
    
    Supports filtering by:
    - provider: Execution provider (e.g. openai)
    - model: Execution model (supports partial match)
    - session_id: All executions in a session
    - agent_id: All executions by an agent
    - prompt_id: All executions using a specific template
    - has_templates: Whether executions are linked to any template
    - min_cost: Only executions with cost >= provided amount
    - start/end: Created_at window
    """
    def _sanitize(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    sanitized_session = _sanitize(session_id)
    sanitized_agent = _sanitize(agent_id)
    sanitized_provider = _sanitize(provider)
    sanitized_model = _sanitize(model)
    sanitized_prompt = _sanitize(prompt_id)
    normalized_start = _normalize_dt(start)
    normalized_end = _normalize_dt(end)

    if normalized_start and normalized_end and normalized_end < normalized_start:
        raise HTTPException(status_code=400, detail="end must be greater than or equal to start")

    default_limit = 25
    max_limit = 1000
    effective_limit = default_limit

    if limit is not None:
        effective_limit = limit
    if page_size is not None:
        effective_limit = page_size

    effective_limit = max(1, min(effective_limit, max_limit))

    base_offset = offset or 0
    if page is not None:
        base_offset = (page - 1) * effective_limit
    effective_offset = max(0, base_offset)

    link_exists = exists().where(template_traces_table.c.trace_id == traces_table.c.trace_id)

    with get_connection(engine) as conn:
        conditions = [traces_table.c.project_id == project_id]

        if sanitized_session:
            conditions.append(traces_table.c.session_id == sanitized_session)
        if sanitized_agent:
            conditions.append(traces_table.c.agent_id == sanitized_agent)
        if sanitized_provider:
            conditions.append(func.lower(traces_table.c.provider) == sanitized_provider.lower())
        if sanitized_model:
            conditions.append(traces_table.c.model.ilike(f"%{sanitized_model}%"))
        if sanitized_prompt:
            prompt_match = exists().where(
                and_(
                    template_traces_table.c.trace_id == traces_table.c.trace_id,
                    template_traces_table.c.prompt_id == sanitized_prompt,
                )
            )
            legacy_prompt_match = traces_table.c.prompt_id == sanitized_prompt
            conditions.append(or_(prompt_match, legacy_prompt_match))
        if has_templates is True:
            conditions.append(link_exists)
        elif has_templates is False:
            conditions.append(~link_exists)
        if min_cost is not None:
            conditions.append(func.coalesce(traces_table.c.cost_usd, 0) >= min_cost)
        if normalized_start:
            conditions.append(traces_table.c.created_at >= normalized_start)
        if normalized_end:
            conditions.append(traces_table.c.created_at <= normalized_end)

        filters = and_(*conditions)

        template_count_subquery = (
            select(func.count(template_traces_table.c.id))
            .where(template_traces_table.c.trace_id == traces_table.c.trace_id)
            .correlate(traces_table)
            .scalar_subquery()
        )

        total_query = select(func.count()).select_from(traces_table).where(filters)
        total_result = conn.execute(total_query)
        total = total_result.scalar_one()

        query = (
            select(
                traces_table.c.trace_id,
                traces_table.c.parent_trace_id,
                traces_table.c.session_id,
                traces_table.c.agent_id,
                traces_table.c.source,
                traces_table.c.provider,
                traces_table.c.model,
                traces_table.c.tokens_in,
                traces_table.c.tokens_out,
                traces_table.c.cost_usd,
                traces_table.c.latency_ms,
                traces_table.c.created_at,
                traces_table.c.metadata,
                template_count_subquery.label("template_count"),
            )
            .where(filters)
            .order_by(desc(traces_table.c.created_at))
            .limit(effective_limit)
            .offset(effective_offset)
        )

        result = conn.execute(query)
        rows = result.fetchall()

    # Get pricing service for cost calculation
    pricing_service = get_pricing_service()

    executions: List[ExecutionListItem] = []
    for row in rows:
        # Calculate cost on-the-fly using current pricing
        cost_usd = row.cost_usd
        if cost_usd is None and row.provider and row.model:
            cost_usd = pricing_service.calculate_cost(
                provider=row.provider,
                model=row.model,
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
            )

        executions.append(
            ExecutionListItem(
                trace_id=row.trace_id,
                parent_trace_id=row.parent_trace_id,
                session_id=row.session_id,
                agent_id=row.agent_id,
                source=row.source,
                provider=row.provider,
                model=row.model,
                tokens_in=row.tokens_in,
                tokens_out=row.tokens_out,
                cost_usd=cost_usd,
                latency_ms=row.latency_ms,
                created_at=row.created_at.isoformat() if row.created_at else None,
                template_count=row.template_count or 0,
                metadata=row.metadata,
            )
        )

    return ExecutionListResponse(
        executions=executions,
        total=total,
        limit=effective_limit,
        offset=effective_offset,
    )


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
                "metadata": template_row.metadata_json,
                "position": template_row.position,
                "role": template_row.role,
                "source": template_row.source,
                "message_index": template_row.message_index,
            }
        )

    return {
        "trace_id": log_row.trace_id,
        "parent_trace_id": log_row.parent_trace_id,
        "session_id": log_row.session_id,
        "agent_id": log_row.agent_id,
        "source": log_row.source,
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


@router.get("/api/projects/{project_id}/executions/{trace_id}/related")
async def get_related_traces(
    project_id: UUID,
    trace_id: str,
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """
    Get related traces (parent, children, siblings) for a given trace.
    
    This helps visualize multi-agent workflows and trace hierarchies.
    """
    with get_connection(engine) as conn:
        # Get the current trace to find its parent
        current_result = conn.execute(
            select(traces_table.c.parent_trace_id, traces_table.c.session_id).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.trace_id == trace_id,
                )
            )
        )
        current_row = current_result.fetchone()
        
        if not current_row:
            raise HTTPException(status_code=404, detail="Trace not found")
        
        parent_trace_id = current_row.parent_trace_id
        session_id = current_row.session_id
        
        # Get parent trace details if exists
        parent_trace = None
        if parent_trace_id:
            parent_result = conn.execute(
                select(
                    traces_table.c.trace_id,
                    traces_table.c.agent_id,
                    traces_table.c.created_at,
                    traces_table.c.latency_ms,
                    traces_table.c.tokens_in,
                    traces_table.c.tokens_out,
                ).where(
                    and_(
                        traces_table.c.project_id == project_id,
                        traces_table.c.trace_id == parent_trace_id,
                    )
                )
            )
            parent_row = parent_result.fetchone()
            if parent_row:
                parent_trace = {
                    "trace_id": parent_row.trace_id,
                    "agent_id": parent_row.agent_id,
                    "created_at": parent_row.created_at.isoformat() if parent_row.created_at else None,
                    "latency_ms": parent_row.latency_ms,
                    "tokens_in": parent_row.tokens_in,
                    "tokens_out": parent_row.tokens_out,
                }
        
        # Get child traces
        children_result = conn.execute(
            select(
                traces_table.c.trace_id,
                traces_table.c.agent_id,
                traces_table.c.created_at,
                traces_table.c.latency_ms,
                traces_table.c.tokens_in,
                traces_table.c.tokens_out,
            ).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.parent_trace_id == trace_id,
                )
            ).order_by(traces_table.c.created_at)
        )
        children_rows = children_result.fetchall()
        
        children = [
            {
                "trace_id": row.trace_id,
                "agent_id": row.agent_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "latency_ms": row.latency_ms,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
            }
            for row in children_rows
        ]
        
        # Get sibling traces (same parent)
        siblings = []
        if parent_trace_id:
            siblings_result = conn.execute(
                select(
                    traces_table.c.trace_id,
                    traces_table.c.agent_id,
                    traces_table.c.created_at,
                    traces_table.c.latency_ms,
                    traces_table.c.tokens_in,
                    traces_table.c.tokens_out,
                ).where(
                    and_(
                        traces_table.c.project_id == project_id,
                        traces_table.c.parent_trace_id == parent_trace_id,
                        traces_table.c.trace_id != trace_id,
                    )
                ).order_by(traces_table.c.created_at)
            )
            siblings_rows = siblings_result.fetchall()
            
            siblings = [
                {
                    "trace_id": row.trace_id,
                    "agent_id": row.agent_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "latency_ms": row.latency_ms,
                    "tokens_in": row.tokens_in,
                    "tokens_out": row.tokens_out,
                }
                for row in siblings_rows
            ]
        
        # Get all traces in the same session to show multi-agent participation
        session_agents = []
        if session_id:
            session_result = conn.execute(
                select(
                    traces_table.c.agent_id,
                    func.count(traces_table.c.id).label("trace_count"),
                ).where(
                    and_(
                        traces_table.c.project_id == project_id,
                        traces_table.c.session_id == session_id,
                        traces_table.c.agent_id.isnot(None),
                    )
                ).group_by(traces_table.c.agent_id)
            )
            session_rows = session_result.fetchall()
            
            session_agents = [
                {
                    "agent_id": row.agent_id,
                    "trace_count": row.trace_count,
                }
                for row in session_rows
            ]
    
    return {
        "trace_id": trace_id,
        "parent": parent_trace,
        "children": children,
        "siblings": siblings,
        "session_agents": session_agents,
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
