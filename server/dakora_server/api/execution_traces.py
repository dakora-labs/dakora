"""API endpoints for trace-based execution logging

This module provides telemetry/observability endpoints for receiving and querying
execution traces from Microsoft Agent Framework middleware and other observability sources.
"""

from datetime import datetime, timezone
from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, and_, func, desc, exists, or_, text, case
from sqlalchemy.engine import Engine

from dakora_server.auth import validate_project_access
from dakora_server.core.database import (
    get_engine,
    get_connection,
    template_traces_table,
    traces_table,
    executions_table,
    execution_messages_table,
)
from dakora_server.core.token_pricing import get_pricing_service
from dakora_server.api.schemas import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionListItem,
    ExecutionListResponse,
)

router = APIRouter()


def _strip_dakora_markers(parts: list[dict]) -> list[dict]:
    """
    Remove Dakora template markers from message parts at API response time.
    Pattern: <!--dakora:prompt_id=...,version=...-->
    This is applied only when serving data to clients, not when storing in DB.
    """
    import re
    pattern = r'<!--dakora:prompt_id=[^,]+,version=[^>]+-->\s*'
    
    cleaned_parts = []
    for part in parts:
        if isinstance(part, dict):
            cleaned_part = part.copy()
            if cleaned_part.get("type") == "text" and isinstance(cleaned_part.get("content"), str):
                cleaned_part["content"] = re.sub(pattern, '', cleaned_part["content"]).strip()
            cleaned_parts.append(cleaned_part)
        else:
            cleaned_parts.append(part)
    
    return cleaned_parts


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
    - Trace and agent tracking
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
        # Write to NEW SCHEMA ONLY (no backward compatibility)
        # 1. Upsert trace-level record
        from datetime import timedelta
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(milliseconds=request.latency_ms or 0)
        
        trace_values = {
            "trace_id": request.trace_id,
            "project_id": project_id,
            "provider": request.provider,
            "start_time": start_time,
            "end_time": end_time,
            "attributes": request.metadata or {},
        }
        
        stmt = pg_insert(traces_table).values(trace_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["trace_id"],
            set_={"end_time": stmt.excluded.end_time}
        )
        conn.execute(stmt)
        
        # 2. Insert chat span into executions
        span_id = f"{request.trace_id}-root"
        execution_values = {
            "trace_id": request.trace_id,
            "span_id": span_id,
            "parent_span_id": request.parent_trace_id,
            "project_id": project_id,
            "type": "chat",
            "span_kind": "INTERNAL",
            "agent_id": request.agent_id,
            "agent_name": request.agent_id,
            "provider": request.provider,
            "model": request.model,
            "start_time": start_time,
            "end_time": end_time,
            "tokens_in": request.tokens_in,
            "tokens_out": request.tokens_out,
            "total_cost_usd": cost_value,
            "status": "OK",
            "attributes": {},
        }
        conn.execute(insert(executions_table).values(execution_values))
        
        # 3. Insert messages from conversation_history
        if request.conversation_history:
            for idx, msg in enumerate(request.conversation_history):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # Map role to direction
                direction = "input" if role in ("user", "system") else "output"
                
                msg_values = {
                    "trace_id": request.trace_id,
                    "span_id": span_id,
                    "direction": direction,
                    "msg_index": idx,
                    "role": role,
                    "parts": [{"type": "text", "content": content}],
                }
                conn.execute(insert(execution_messages_table).values(msg_values))

        # 4. Link to templates if provided
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
    
    Queries the new OTLP-native schema (executions table).
    
    Supports filtering by:
    - provider: Execution provider (e.g. openai)
    - model: Execution model (supports partial match)
    - agent_id: All executions by an agent
    - prompt_id: All executions using a specific template (✓ implemented for new schema)
    - has_templates: Whether executions are linked to any template (✓ implemented for new schema)
    - min_cost: Only executions with cost >= provided amount
    - start/end: Created_at window
    
    Note: In the new schema, agent_name is mapped to agent_id for backward compatibility
    with existing API clients expecting the agent_id field.
    """
    def _sanitize(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    def _normalize_dt(value: Optional[datetime]) -> Optional[datetime]:
        """Normalize datetime to UTC, keeping timezone awareness for proper comparisons."""
        if value is None:
            return None
        if value.tzinfo:
            return value.astimezone(timezone.utc)
        # If naive datetime is provided, assume it's already UTC
        return value.replace(tzinfo=timezone.utc)

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

    with get_connection(engine) as conn:
        # NEW SCHEMA QUERY (always - no fallback)
        # Group by trace_id to show one row per trace (entire conversation/workflow)
        # Aggregate all spans within each trace for total metrics
            
            # Apply filters on executions for agent, provider, model, cost, time
            # IMPORTANT: Only aggregate 'chat' spans (actual LLM calls) to avoid double-counting
            # 'agent' spans are wrappers that contain agent context but delegate to child 'chat' spans
            # We'll join with parent agent spans to get agent_name/agent_id context
            execution_conditions = [
                executions_table.c.project_id == project_id,  # Filter by project directly
                executions_table.c.type == "chat",  # Only chat spans have the actual tokens/costs
                # Ensure chat spans have meaningful LLM data (not orchestration-only)
                or_(
                    executions_table.c.tokens_in.isnot(None),
                    executions_table.c.tokens_out.isnot(None),
                    executions_table.c.provider.isnot(None),
                    executions_table.c.model.isnot(None)
                )
            ]
            if sanitized_provider:
                execution_conditions.append(func.lower(executions_table.c.provider) == sanitized_provider.lower())
            if sanitized_model:
                execution_conditions.append(executions_table.c.model.ilike(f"%{sanitized_model}%"))
            if normalized_start:
                execution_conditions.append(executions_table.c.start_time >= normalized_start)
            if normalized_end:
                execution_conditions.append(executions_table.c.start_time <= normalized_end)
            
            # Create alias for parent agent spans to get agent context
            parent_agent = executions_table.alias("parent_agent")
            
            # Build subquery to get trace-level aggregates (only from chat spans)
            # Join with parent agent spans to get agent_name when available
            trace_agg_subq = (
                select(
                    executions_table.c.trace_id,
                    func.min(executions_table.c.start_time).label("first_start_time"),
                    func.max(executions_table.c.start_time).label("last_start_time"),
                    func.sum(executions_table.c.tokens_in).label("total_tokens_in"),
                    func.sum(executions_table.c.tokens_out).label("total_tokens_out"),
                    func.sum(executions_table.c.total_cost_usd).label("total_cost_usd"),
                    # Get agent name from parent agent span if exists, otherwise from chat span itself
                    func.max(func.coalesce(parent_agent.c.agent_name, executions_table.c.agent_name)).label("agent_name"),
                    # Get provider/model from chat spans (they have the actual LLM info)
                    func.max(executions_table.c.provider).label("provider"),
                    func.max(executions_table.c.model).label("model"),
                )
                .select_from(
                    executions_table.outerjoin(
                        parent_agent,
                        and_(
                            executions_table.c.trace_id == parent_agent.c.trace_id,
                            executions_table.c.parent_span_id == parent_agent.c.span_id,
                            parent_agent.c.type == "agent"  # Only join to agent-type parents
                        )
                    )
                )
                .where(and_(*execution_conditions))
            )
            
            # Apply agent filter if provided (check both chat span and parent agent span)
            if sanitized_agent:
                trace_agg_subq = trace_agg_subq.where(
                    or_(
                        executions_table.c.agent_name == sanitized_agent,
                        parent_agent.c.agent_name == sanitized_agent
                    )
                )
            
            trace_agg_subq = trace_agg_subq.group_by(executions_table.c.trace_id).subquery()
            
            # Apply trace-level filters (no longer need conditions list for traces_table)
            trace_filters = []
            if min_cost is not None:
                trace_filters.append(func.coalesce(trace_agg_subq.c.total_cost_usd, 0) >= min_cost)
            
            # Template filters - check template_traces_table for template linkage
            if sanitized_prompt:
                # Filter traces that are linked to a specific prompt_id
                prompt_match = exists().where(
                    and_(
                        template_traces_table.c.trace_id == trace_agg_subq.c.trace_id,
                        template_traces_table.c.prompt_id == sanitized_prompt,
                    )
                )
                trace_filters.append(prompt_match)
            
            if has_templates is True:
                # Filter traces that have at least one template linkage
                template_exists = exists().where(
                    template_traces_table.c.trace_id == trace_agg_subq.c.trace_id
                )
                trace_filters.append(template_exists)
            elif has_templates is False:
                # Filter traces that have no template linkages
                template_exists = exists().where(
                    template_traces_table.c.trace_id == trace_agg_subq.c.trace_id
                )
                trace_filters.append(~template_exists)
            
            # Count total traces
            total_query = select(func.count()).select_from(trace_agg_subq)
            if trace_filters:
                total_query = total_query.where(and_(*trace_filters))
            total = conn.execute(total_query).scalar_one()
            
            # Main query - get traces with aggregated metrics from chat spans (WITHOUT template count)
            # Template counting happens AFTER pagination for better performance
            # Join with traces table to get the overall trace duration (user-facing latency)
            query = (
                select(
                    trace_agg_subq.c.trace_id,
                    trace_agg_subq.c.first_start_time.label("created_at"),
                    trace_agg_subq.c.agent_name,
                    trace_agg_subq.c.provider,
                    trace_agg_subq.c.model,
                    trace_agg_subq.c.total_tokens_in,
                    trace_agg_subq.c.total_tokens_out,
                    traces_table.c.duration_ms.label("latency_ms"),  # Use trace duration instead of max chat latency
                    trace_agg_subq.c.total_cost_usd,
                )
                .select_from(
                    trace_agg_subq.join(
                        traces_table,
                        trace_agg_subq.c.trace_id == traces_table.c.trace_id
                    )
                )
            )
            if trace_filters:
                query = query.where(and_(*trace_filters))
            query = query.order_by(desc(trace_agg_subq.c.first_start_time)).limit(effective_limit).offset(effective_offset)
            
            result = conn.execute(query)
            rows = result.fetchall()
            
            # Now fetch all metadata ONLY for the paginated trace_ids (much more efficient)
            # OPTIMIZATION: Combine span stats, agent/model detection, and error checking into ONE query
            template_count_map: dict[str, int] = {}
            span_count_map: dict[str, int] = {}
            span_type_map: dict[str, dict[str, int]] = {}
            unique_agents_map: dict[str, list[str]] = {}
            unique_models_map: dict[str, list[str]] = {}
            error_map: dict[str, tuple[bool, str | None]] = {}
            
            if rows:
                trace_ids_in_page = [row.trace_id for row in rows]
                
                # Query 1: Get template counts (separate table, must be separate)
                template_counts_result = conn.execute(
                    select(
                        template_traces_table.c.trace_id,
                        func.count(template_traces_table.c.id).label("template_count")
                    )
                    .where(template_traces_table.c.trace_id.in_(trace_ids_in_page))
                    .group_by(template_traces_table.c.trace_id)
                )
                template_count_map = {
                    row.trace_id: int(row.template_count)
                    for row in template_counts_result.fetchall()
                }
                
                # Query 2: COMBINED span metadata query
                # Get ALL span-level metadata in a single query using conditional aggregations
                combined_stats_result = conn.execute(
                    select(
                        executions_table.c.trace_id,
                        executions_table.c.type,
                        # Span counts per type
                        func.count(executions_table.c.span_id).label("span_count"),
                        # Error detection
                        func.max(
                            case(
                                (executions_table.c.status == "ERROR", 1),
                                else_=0
                            )
                        ).label("has_error"),
                        func.max(
                            case(
                                (executions_table.c.status == "ERROR", executions_table.c.status_message),
                                else_=None
                            )
                        ).label("error_message"),
                    )
                    .where(executions_table.c.trace_id.in_(trace_ids_in_page))
                    .group_by(executions_table.c.trace_id, executions_table.c.type)
                )
                
                # Process combined results
                for row in combined_stats_result.fetchall():
                    trace_id = row.trace_id
                    span_type = row.type or "unknown"
                    count = int(row.span_count)
                    
                    # Update span counts
                    span_count_map[trace_id] = span_count_map.get(trace_id, 0) + count
                    if trace_id not in span_type_map:
                        span_type_map[trace_id] = {}
                    span_type_map[trace_id][span_type] = count
                    
                    # Update error status (take max across all span types)
                    current_error = error_map.get(trace_id, (False, None))
                    if row.has_error == 1:
                        error_map[trace_id] = (True, row.error_message or current_error[1])
                
                # Query 3: Get unique agents AND models in a single query using FILTER
                # This combines what were previously two separate queries into one
                agent_model_stats_result = conn.execute(
                    select(
                        executions_table.c.trace_id,
                        func.array_agg(
                            func.distinct(executions_table.c.agent_name)
                        ).filter(
                            and_(
                                executions_table.c.type == "agent",
                                executions_table.c.agent_name.isnot(None)
                            )
                        ).label("agent_names"),
                        func.array_agg(
                            func.distinct(executions_table.c.model)
                        ).filter(
                            and_(
                                executions_table.c.type == "chat",
                                executions_table.c.model.isnot(None)
                            )
                        ).label("model_names"),
                    )
                    .where(executions_table.c.trace_id.in_(trace_ids_in_page))
                    .group_by(executions_table.c.trace_id)
                )
                
                for row in agent_model_stats_result.fetchall():
                    if row.agent_names:
                        unique_agents_map[row.trace_id] = row.agent_names
                    if row.model_names:
                        unique_models_map[row.trace_id] = row.model_names
            
            executions: List[ExecutionListItem] = []
            for row in rows:
                trace_id = row.trace_id
                has_errors, error_message = error_map.get(trace_id, (False, None))
                
                executions.append(
                    ExecutionListItem(
                        trace_id=trace_id,
                        parent_trace_id=None,  # Not tracked in new schema at trace level
                        session_id=None,  # TODO: Extract from attributes if needed
                        agent_id=row.agent_name,  # Map agent_name to agent_id for compatibility
                        source="otlp",
                        provider=row.provider,
                        model=row.model,
                        tokens_in=None,  # Not used for trace-grouped results
                        tokens_out=None,  # Not used for trace-grouped results
                        total_tokens_in=int(row.total_tokens_in) if row.total_tokens_in else None,
                        total_tokens_out=int(row.total_tokens_out) if row.total_tokens_out else None,
                        cost_usd=float(row.total_cost_usd) if row.total_cost_usd else None,
                        latency_ms=row.latency_ms,
                        created_at=row.created_at.isoformat() if row.created_at else None,
                        template_count=template_count_map.get(trace_id, 0),
                        metadata={},
                        # New Priority 1 fields
                        span_count=span_count_map.get(trace_id, 0),
                        span_type_breakdown=span_type_map.get(trace_id),
                        has_errors=has_errors,
                        error_message=error_message,
                        # Multi-agent/model detection
                        unique_agents=unique_agents_map.get(trace_id),
                        unique_models=unique_models_map.get(trace_id),
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
    span_id: Optional[str] = Query(None, description="Specific span ID to retrieve (defaults to root span)"),
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """
    Get detailed execution log including conversation history and linked templates.
    
    Uses the new OTLP-native schema with messages and hierarchy.
    If span_id is not provided, automatically selects the most meaningful span:
      1. First 'chat' span (actual LLM call with messages) - preferred
      2. First 'agent' span (agent invocation) - fallback
      3. Any other span - last resort
    
    This ensures users see relevant conversation data instead of orchestration-only spans.
    """
    with get_connection(engine) as conn:
        # NEW SCHEMA QUERY (always - no fallback)
        # If span_id not provided, find the most meaningful span to display
        if not span_id:
            # Prefer chat spans (actual LLM calls with messages)
            # Fall back to agent spans if no chat spans exist
            # Only use root span as last resort (might be workflow.run)
            meaningful_span_result = conn.execute(
                select(executions_table.c.span_id, executions_table.c.type)
                .where(executions_table.c.trace_id == trace_id)
                .order_by(
                    # Prioritize: chat > agent > others
                    # Then by start_time to get the first one
                    case(
                        (executions_table.c.type == "chat", 1),
                        (executions_table.c.type == "agent", 2),
                        else_=3
                    ),
                    executions_table.c.start_time
                )
                .limit(1)
            )
            span_row = meaningful_span_result.fetchone()
            if not span_row:
                raise HTTPException(status_code=404, detail="Execution not found")
            span_id = span_row.span_id
        
        # Get execution details
        exec_result = conn.execute(
            select(executions_table).where(
                and_(
                    executions_table.c.trace_id == trace_id,
                    executions_table.c.span_id == span_id
                )
            )
        )
        exec_row = exec_result.fetchone()
        
        if not exec_row:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Get input messages from the FIRST chat span only (initial user input + context)
        # In multi-agent workflows, subsequent spans receive previous outputs as input context,
        # which creates duplicates. We only need the initial input from the first agent.
        first_chat_span = conn.execute(
            select(executions_table.c.span_id)
            .where(
                and_(
                    executions_table.c.trace_id == trace_id,
                    executions_table.c.type == "chat"
                )
            )
            .order_by(executions_table.c.start_time)
            .limit(1)
        ).scalar_one_or_none()
        
        input_messages = []
        if first_chat_span:
            input_msgs_result = conn.execute(
                select(
                    execution_messages_table.c.role,
                    execution_messages_table.c.parts,
                    execution_messages_table.c.msg_index,
                    execution_messages_table.c.finish_reason,
                    execution_messages_table.c.span_id,
                )
                .where(
                    and_(
                        execution_messages_table.c.trace_id == trace_id,
                        execution_messages_table.c.span_id == first_chat_span,
                        execution_messages_table.c.direction == "input"
                    )
                )
                .order_by(execution_messages_table.c.msg_index)
            )
            for msg_row in input_msgs_result.fetchall():
                input_messages.append({
                    "role": msg_row.role,
                    "parts": _strip_dakora_markers(msg_row.parts) if msg_row.parts else [],
                    "msg_index": msg_row.msg_index,
                    "finish_reason": msg_row.finish_reason,
                    "span_id": msg_row.span_id,
                    "span_type": "chat",  # We know it's a chat span
                })
        
        # Get ALL output messages from ALL chat spans
        # Each output is unique - it's what each agent produced
        # This gives us the workflow progression without duplicates
        # Join with parent agent spans to get agent names
        parent_agent_alias = executions_table.alias("parent_agent")
        
        output_msgs_result = conn.execute(
            select(
                execution_messages_table.c.role,
                execution_messages_table.c.parts,
                execution_messages_table.c.msg_index,
                execution_messages_table.c.finish_reason,
                execution_messages_table.c.span_id,
                executions_table.c.start_time,
                parent_agent_alias.c.agent_name.label('agent_name')
            )
            .select_from(
                execution_messages_table.join(
                    executions_table,
                    and_(
                        execution_messages_table.c.trace_id == executions_table.c.trace_id,
                        execution_messages_table.c.span_id == executions_table.c.span_id
                    )
                ).outerjoin(
                    parent_agent_alias,
                    and_(
                        executions_table.c.trace_id == parent_agent_alias.c.trace_id,
                        executions_table.c.parent_span_id == parent_agent_alias.c.span_id,
                        parent_agent_alias.c.type == "agent"
                    )
                )
            )
            .where(
                and_(
                    execution_messages_table.c.trace_id == trace_id,
                    execution_messages_table.c.direction == "output",
                    executions_table.c.type == "chat"
                )
            )
            .order_by(executions_table.c.start_time, execution_messages_table.c.msg_index)
        )
        output_messages = []
        for msg_row in output_msgs_result.fetchall():
            output_messages.append({
                "role": msg_row.role,
                "parts": _strip_dakora_markers(msg_row.parts) if msg_row.parts else [],
                "msg_index": msg_row.msg_index,
                "finish_reason": msg_row.finish_reason,
                "span_id": msg_row.span_id,
                "span_type": "chat",
                "agent_name": msg_row.agent_name,  # Add agent name for display
            })
        
        # Get child spans - return ALL spans in trace for better visibility
        # (Priority 2: Changed from direct children only to all descendants)
        children_result = conn.execute(
            select(
                executions_table.c.span_id,
                executions_table.c.type,
                executions_table.c.agent_name,
                executions_table.c.latency_ms,
                executions_table.c.tokens_in,
                executions_table.c.tokens_out,
                executions_table.c.status,
                executions_table.c.start_time,
            )
            .where(
                and_(
                    executions_table.c.trace_id == trace_id,
                    executions_table.c.span_id != span_id  # Exclude current span, include all others
                )
            )
            .order_by(executions_table.c.start_time)
        )
        child_spans = []
        for child_row in children_result.fetchall():
            child_spans.append({
                "span_id": child_row.span_id,
                "type": child_row.type,
                "agent_name": child_row.agent_name,
                "latency_ms": child_row.latency_ms,
                "tokens_in": child_row.tokens_in,
                "tokens_out": child_row.tokens_out,
                "status": child_row.status,
                "start_time": child_row.start_time.isoformat() if child_row.start_time else None,
            })
        
        # Get linked templates from template_traces table
        template_result = conn.execute(
            select(template_traces_table)
            .where(template_traces_table.c.trace_id == trace_id)
            .order_by(template_traces_table.c.position)
        )
        template_rows = template_result.fetchall()

        templates_used: List[dict[str, Any]] = []
        for template_row in template_rows:
            templates_used.append({
                "prompt_id": template_row.prompt_id,
                "version": template_row.version,
                "inputs": template_row.inputs_json or {},
                "position": template_row.position,
                "role": template_row.role,
                "source": template_row.source,
                "message_index": template_row.message_index,
            })
        
        return {
            "trace_id": exec_row.trace_id,
            "span_id": exec_row.span_id,
            "type": exec_row.type,
            "agent_name": exec_row.agent_name,
            "provider": exec_row.provider,
            "model": exec_row.model,
            "start_time": exec_row.start_time.isoformat() if exec_row.start_time else None,
            "latency_ms": exec_row.latency_ms,
            "tokens_in": exec_row.tokens_in,
            "tokens_out": exec_row.tokens_out,
            "total_cost_usd": float(exec_row.total_cost_usd) if exec_row.total_cost_usd else None,
            "status": exec_row.status,
            "status_message": exec_row.status_message,
            "input_messages": input_messages,
            "output_messages": output_messages,
            "child_spans": child_spans,
            "template_usages": templates_used,  # Add templates to response
            "attributes": exec_row.attributes or {},
            # Backward compatibility
            "created_at": exec_row.start_time.isoformat() if exec_row.start_time else None,
        }


@router.get("/api/projects/{project_id}/executions/{trace_id}/hierarchy")
async def get_execution_hierarchy(
    project_id: UUID,
    trace_id: str,
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    """
    Get full span hierarchy for a trace using recursive CTE.
    
    Returns a tree of all spans in the trace, ordered by execution path.
    Only works with new OTLP-native schema.
    """
    with get_connection(engine) as conn:
        # Check if trace exists in new schema
        # Use exists check instead of count for better performance
        trace_exists = conn.execute(
            select(1)
            .select_from(
                executions_table.join(
                    traces_table,
                    executions_table.c.trace_id == traces_table.c.trace_id
                )
            )
            .where(
                and_(
                    traces_table.c.project_id == project_id,
                    executions_table.c.trace_id == trace_id
                )
            )
            .limit(1)
        ).scalar_one_or_none()
        
        if trace_exists is None:
            raise HTTPException(
                status_code=404, 
                detail="Trace not found in new schema. Hierarchy only available for OTLP-native traces."
            )
        
        # Recursive CTE to build span tree
        query = text("""
            WITH RECURSIVE span_tree AS (
                -- Base case: root span(s)
                SELECT 
                    trace_id, span_id, parent_span_id, type, agent_name,
                    latency_ms, tokens_in, tokens_out, start_time,
                    0 AS depth, 
                    ARRAY[span_id] AS path
                FROM executions
                WHERE trace_id = :trace_id AND parent_span_id IS NULL
                
                UNION ALL
                
                -- Recursive case: child spans
                SELECT 
                    e.trace_id, e.span_id, e.parent_span_id, e.type, e.agent_name,
                    e.latency_ms, e.tokens_in, e.tokens_out, e.start_time,
                    st.depth + 1, 
                    st.path || e.span_id
                FROM executions e
                JOIN span_tree st ON e.parent_span_id = st.span_id
                WHERE e.trace_id = st.trace_id
            )
            SELECT * FROM span_tree ORDER BY path
        """)
        
        result = conn.execute(query, {"trace_id": trace_id})
        rows = result.fetchall()
        
        spans = []
        for row in rows:
            spans.append({
                "span_id": row.span_id,
                "parent_span_id": row.parent_span_id,
                "type": row.type,
                "agent_name": row.agent_name,
                "latency_ms": row.latency_ms,
                "tokens_in": row.tokens_in,
                "tokens_out": row.tokens_out,
                "depth": row.depth,
                "start_time": row.start_time.isoformat() if row.start_time else None,
            })
        
        return {
            "trace_id": trace_id,
            "spans": spans,
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
        # Check if trace exists in new schema
        new_trace_check = conn.execute(
            select(traces_table.c.trace_id).where(
                and_(
                    traces_table.c.project_id == project_id,
                    traces_table.c.trace_id == trace_id,
                )
            )
        ).fetchone()
        
        # If trace is in new schema, return empty relations
        # (new schema doesn't support trace-level parent/child relationships)
        if new_trace_check:
            # Get agent names from executions for multi-agent session info
            agents_result = conn.execute(
                select(
                    executions_table.c.agent_name,
                    func.count().label("trace_count"),
                ).where(
                    and_(
                        executions_table.c.trace_id == trace_id,
                        executions_table.c.project_id == project_id,
                        executions_table.c.agent_name.isnot(None),
                    )
                ).group_by(executions_table.c.agent_name)
            )
            agents_rows = agents_result.fetchall()
            
            session_agents = [
                {
                    "agent_id": row.agent_name,
                    "trace_count": row.trace_count,
                }
                for row in agents_rows
            ]
            
            return {
                "trace_id": trace_id,
                "parent": None,
                "children": [],
                "siblings": [],
                "session_agents": session_agents,
            }
        
        # Trace not found in new schema
        raise HTTPException(status_code=404, detail="Trace not found")


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
        # Query new schema: aggregate from executions (chat spans only) joined with template_traces
        result = conn.execute(
            select(
                func.count(func.distinct(traces_table.c.trace_id)).label("total_executions"),
                func.sum(executions_table.c.total_cost_usd).label("total_cost_usd"),
                func.avg(traces_table.c.duration_ms).label("avg_latency_ms"),
                func.sum(executions_table.c.tokens_in).label("total_tokens_in"),
                func.sum(executions_table.c.tokens_out).label("total_tokens_out"),
            )
            .select_from(
                template_traces_table.join(
                    traces_table,
                    template_traces_table.c.trace_id == traces_table.c.trace_id
                ).join(
                    executions_table,
                    and_(
                        traces_table.c.trace_id == executions_table.c.trace_id,
                        executions_table.c.type == "chat"  # Only count chat spans for metrics
                    )
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
