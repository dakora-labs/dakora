"""OTLP trace processing orchestration.

This module handles the extraction of execution traces from OTLP spans.

Architecture:
- Fast path: When complete traces arrive in one batch, extract immediately
- Recompute path: When late spans arrive, recompute with full context from DB

Future optimization points:
- Make recompute async (background worker)
- Add trace completion detection
- Add extraction result caching
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from dakora_server.core.database import (
    executions_new_table,
    execution_messages_new_table,
    otel_spans_table,
    template_traces_table,
    tool_invocations_new_table,
    traces_new_table,
    traces_table,
)
from dakora_server.core.otlp_extractor import (
    build_span_hierarchy,
    extract_execution_trace,
    extract_template_usages_from_messages,
    is_root_execution_span,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from dakora_server.api.otlp_traces import OTLPSpan

logger = logging.getLogger(__name__)


def process_trace_batch(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> dict[str, int]:
    """
    Process a batch of OTLP spans with smart extraction strategy.

    Strategy:
    1. Store all incoming spans in otel_spans table
    2. For each unique trace_id in the batch:
       - If NEW trace: extract immediately with spans from batch
       - If EXISTING trace: trigger recompute with all spans from DB

    This handles:
    - Fast path: Complete traces in one batch (99% case) → instant extraction
    - Late arrivals: Spans arrive after initial trace → eventually consistent

    Args:
        spans: List of OTLP spans to process
        project_id: Project UUID
        conn: Database connection

    Returns:
        Statistics dict with keys:
        - spans_stored: Number of spans stored
        - executions_created: Number of new executions
        - recomputes: Number of trace recomputes triggered
    """
    if not spans:
        return {"spans_stored": 0, "executions_created": 0, "recomputes": 0}

    stats = {"spans_stored": 0, "executions_created": 0, "recomputes": 0}

    # Step 1: Store all incoming spans
    for span in spans:
        _store_span(span, project_id, conn)
        stats["spans_stored"] += 1

    # Step 2: Process each unique trace
    trace_ids = _get_unique_trace_ids(spans)

    for trace_id in trace_ids:
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        if _is_new_trace(trace_id, conn):
            # Fast path: Extract immediately with current batch
            logger.info(f"New trace {trace_id}, extracting from batch")
            created = _extract_executions_from_batch(
                trace_spans, project_id, conn
            )
            stats["executions_created"] += created
        else:
            # Recompute path: Late-arriving spans, recompute with full context
            logger.info(f"Existing trace {trace_id}, triggering recompute")
            _recompute_trace(trace_id, project_id, conn)
            stats["recomputes"] += 1

    return stats


def _store_span(span: OTLPSpan, project_id: UUID, conn: Connection) -> None:
    """
    Store a single OTLP span in the database.

    Uses ON CONFLICT DO NOTHING for idempotency - if exporter retries,
    we don't duplicate spans.
    """
    duration_ns = span.end_time_ns - span.start_time_ns

    stmt = insert(otel_spans_table).values(
        trace_id=span.trace_id,
        span_id=span.span_id,
        parent_span_id=span.parent_span_id,
        project_id=project_id,
        span_name=span.span_name,
        span_kind=span.span_kind,
        attributes=span.attributes,
        events=span.events,
        start_time_ns=span.start_time_ns,
        end_time_ns=span.end_time_ns,
        duration_ns=duration_ns,
        status_code=span.status_code,
        status_message=span.status_message,
    ).on_conflict_do_nothing(
        index_elements=['span_id']
    )

    conn.execute(stmt)


def _get_unique_trace_ids(spans: list[OTLPSpan]) -> list[str]:
    """Extract unique trace IDs from span batch."""
    return list(set(span.trace_id for span in spans))


def _is_new_trace(trace_id: str, conn: Connection) -> bool:
    """
    Check if this is the first time we're seeing this trace.

    We consider a trace "new" if there are no traces in the NEW schema for it yet.
    This ensures we use the fast path for first batch and recompute path for late arrivals.
    
    Note: We check traces_new_table (not traces_table/execution_traces) because
    the new schema is the source of truth for span-based executions.
    """
    result = conn.execute(
        select(traces_new_table.c.trace_id)
        .where(traces_new_table.c.trace_id == trace_id)
        .limit(1)
    )
    return result.first() is None


def _extract_executions_from_batch(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> int:
    """
    Extract execution traces from current batch (fast path).

    Builds span hierarchy once for O(1) child lookups.

    Args:
        spans: Spans for a single trace_id
        project_id: Project UUID
        conn: Database connection

    Returns:
        Number of executions created
    """
    executions_created = 0

    # Build span hierarchy once (O(n)) for efficient child lookups (O(1) per lookup)
    span_hierarchy = build_span_hierarchy(spans)

    # DUAL-WRITE: Write to new schema (all spans)
    _write_to_new_schema(spans, project_id, conn)

    # Find root execution spans (for old schema)
    for span in spans:
        if not is_root_execution_span(span):
            continue

        # Extract execution trace
        trace_data = extract_execution_trace(
            root_span=span,
            span_hierarchy=span_hierarchy,
            project_id=project_id,
        )

        # DUAL-WRITE: Upsert to OLD execution_traces table (handles race conditions on recompute)
        stmt = insert(traces_table).values(**trace_data).on_conflict_do_update(
            index_elements=['trace_id'],
            set_=trace_data
        )
        conn.execute(stmt)

        # Insert template linkages (old schema)
        template_usages = extract_template_usages_from_messages(span)
        if template_usages:
            for usage in template_usages:
                conn.execute(
                    insert(template_traces_table).values(
                        trace_id=span.trace_id,
                        prompt_id=usage["prompt_id"],
                        version=usage["version"],
                        inputs_json=usage["inputs_json"],
                        position=usage["position"],
                        role=usage.get("role"),
                        source=usage.get("source"),
                        message_index=usage.get("message_index"),
                        metadata_json=usage.get("metadata_json"),
                    )
                )

        executions_created += 1
        logger.debug(f"Created execution trace for span {span.span_id}")

    return executions_created


def _recompute_trace(trace_id: str, project_id: UUID, conn: Connection) -> None:
    """
    Recompute execution traces with complete span set from database.

    This is triggered when late-arriving spans are detected for an existing trace.

    Future optimization: Make this async by enqueueing to a background worker.

    Args:
        trace_id: Trace ID to recompute
        project_id: Project UUID
        conn: Database connection
    """
    # Load all spans for this trace from DB
    all_spans = _load_all_spans_for_trace(trace_id, conn)

    if not all_spans:
        logger.warning(f"No spans found for trace {trace_id} during recompute")
        return

    logger.info(f"Recomputing trace {trace_id} with {len(all_spans)} total spans")

    # Delete template linkages (execution trace uses UPSERT now)
    _delete_template_linkages(trace_id, conn)

    # Re-extract with full context (will UPSERT execution trace)
    _extract_executions_from_batch(all_spans, project_id, conn)


def _load_all_spans_for_trace(trace_id: str, conn: Connection) -> list[OTLPSpan]:
    """
    Load all stored spans for a trace from database.

    Reconstructs OTLPSpan objects from database rows.
    """
    from dakora_server.api.otlp_traces import OTLPSpan

    result = conn.execute(
        select(otel_spans_table).where(otel_spans_table.c.trace_id == trace_id)
    )

    spans = []
    for row in result:
        spans.append(
            OTLPSpan(
                trace_id=row.trace_id,
                span_id=row.span_id,
                parent_span_id=row.parent_span_id,
                span_name=row.span_name,
                span_kind=row.span_kind,
                attributes=row.attributes or {},
                events=row.events or [],
                start_time_ns=row.start_time_ns,
                end_time_ns=row.end_time_ns,
                status_code=row.status_code,
                status_message=row.status_message,
            )
        )

    return spans


def _delete_template_linkages(trace_id: str, conn: Connection) -> None:
    """
    Delete existing template linkages for a trace.

    Used before recomputing to clear old template linkages.
    Execution trace itself uses UPSERT so no need to delete.
    """
    conn.execute(delete(template_traces_table).where(template_traces_table.c.trace_id == trace_id))
    logger.debug(f"Deleted template linkages for trace {trace_id}")


# =====================================================================
# NEW SCHEMA DUAL-WRITE FUNCTIONS
# =====================================================================

def _sort_spans_topologically(spans: list[OTLPSpan]) -> list[OTLPSpan]:
    """
    Sort spans in topological order (parents before children).
    
    This ensures that when we insert spans into the executions table,
    parent spans exist before we try to insert child spans that reference them.
    
    Only sorts spans whose parents are in the current batch. Spans with
    external parents are handled separately.
    
    Args:
        spans: List of spans to sort
        
    Returns:
        Sorted list with parents before children
    """
    # Build a map of span_id -> span for quick lookup
    span_map = {span.span_id: span for span in spans}
    
    # Build a map of span_id -> list of child span_ids
    children_map: dict[str, list[str]] = {}
    root_spans: list[str] = []
    spans_with_external_parents: list[OTLPSpan] = []
    
    for span in spans:
        if span.parent_span_id is None:
            # True root span
            root_spans.append(span.span_id)
        elif span.parent_span_id not in span_map:
            # Parent not in this batch - handle separately
            spans_with_external_parents.append(span)
        else:
            # Parent is in this batch
            if span.parent_span_id not in children_map:
                children_map[span.parent_span_id] = []
            children_map[span.parent_span_id].append(span.span_id)
    
    # Perform depth-first traversal to get topological order
    result: list[OTLPSpan] = []
    visited: set[str] = set()
    
    def visit(span_id: str) -> None:
        """Recursively visit span and its children."""
        if span_id in visited:
            return
        
        visited.add(span_id)
        
        # Add the span itself
        if span_id in span_map:
            result.append(span_map[span_id])
        
        # Visit all children
        for child_id in children_map.get(span_id, []):
            visit(child_id)
    
    # Visit all root spans
    for root_id in root_spans:
        visit(root_id)
    
    # Add spans with external parents at the end
    # (these will be handled by checking DB for parent existence)
    result.extend(spans_with_external_parents)
    
    return result


def _write_to_new_schema(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> None:
    """
    Write spans to new normalized schema (dual-write).
    
    This writes to:
    - traces (one per trace_id)
    - executions (all spans with hierarchy)
    - execution_messages (input/output messages)
    - tool_invocations (when tool calls detected)
    
    Args:
        spans: Spans for a single trace_id
        project_id: Project UUID
        conn: Database connection
    """
    if not spans:
        return
    
    trace_id = spans[0].trace_id
    
    # Step 1: Upsert trace record
    _upsert_trace_record(spans, project_id, conn)
    
    # Step 2: Sort spans in topological order (parents before children)
    # This ensures foreign key constraints are satisfied
    sorted_spans = _sort_spans_topologically(spans)
    
    # Step 3: Create execution records for ALL spans in correct order
    for span in sorted_spans:
        _upsert_execution_record(span, project_id, conn)
        
        # Step 4: Extract and store messages
        _extract_and_store_messages(span, conn)
        
        # Step 5: Extract and store tool invocations
        _extract_and_store_tools(span, conn)
    
    logger.debug(f"Wrote {len(spans)} spans to new schema for trace {trace_id}")


def _upsert_trace_record(
    spans: list[OTLPSpan],
    project_id: UUID,
    conn: Connection,
) -> None:
    """Create or update trace-level record."""
    from datetime import datetime, timezone
    
    trace_id = spans[0].trace_id
    
    # Find earliest start and latest end
    start_time_ns = min(s.start_time_ns for s in spans)
    end_time_ns = max(s.end_time_ns for s in spans)
    
    # Convert nanoseconds to datetime
    start_time = datetime.fromtimestamp(start_time_ns / 1_000_000_000, tz=timezone.utc)
    end_time = datetime.fromtimestamp(end_time_ns / 1_000_000_000, tz=timezone.utc)
    
    # Extract provider from any span that has it
    provider = None
    for span in spans:
        attrs = span.attributes or {}
        raw_provider = attrs.get("dakora.span_source")
        if not provider:
            provider = raw_provider
            break
    
    # Aggregate attributes from all spans
    attributes = {}
    for span in spans:
        if span.attributes:
            # Collect dakora.* attributes
            for key, value in span.attributes.items():
                if key.startswith("dakora."):
                    attributes[key] = value
    
    trace_data = {
        "trace_id": trace_id,
        "project_id": project_id,
        "provider": provider,
        "start_time": start_time,
        "end_time": end_time,
        "attributes": attributes if attributes else None,
    }
    
    stmt = insert(traces_new_table).values(**trace_data).on_conflict_do_update(
        index_elements=['trace_id'],
        set_=trace_data
    )
    conn.execute(stmt)


def _upsert_execution_record(
    span: OTLPSpan,
    project_id: UUID,
    conn: Connection,
) -> None:
    """
    Create or update execution record for a single span.
    
    Handles missing parents gracefully by checking if parent exists in DB.
    If parent doesn't exist yet, sets parent_span_id to NULL temporarily.
    Parent will be linked when recompute is triggered by late-arriving parent span.
    """
    from datetime import datetime, timezone
    from dakora_server.core.otlp_extractor import normalize_model, normalize_provider
    
    attrs = span.attributes or {}
    
    # Check if parent exists in database (if span has a parent)
    parent_span_id = span.parent_span_id
    if parent_span_id is not None:
        result = conn.execute(
            select(executions_new_table.c.span_id)
            .where(executions_new_table.c.trace_id == span.trace_id)
            .where(executions_new_table.c.span_id == parent_span_id)
            .limit(1)
        )
        parent_exists = result.first() is not None
        
        if not parent_exists:
            logger.warning(
                f"Parent span {parent_span_id[:8]} not found for span {span.span_id[:8]} "
                f"in trace {span.trace_id[:8]}. Setting parent to NULL temporarily. "
                f"Will be linked on recompute when parent arrives."
            )
            parent_span_id = None
    
    # Extract type from span name or operation
    span_type = _determine_span_type(span)
    
    # Extract fields
    agent_id = attrs.get("gen_ai.agent.id")
    agent_name = attrs.get("gen_ai.agent.name")
    
    # Model and provider
    raw_model = (
        attrs.get("gen_ai.response.model")
        or attrs.get("gen_ai.request.model")
    )
    model = normalize_model(raw_model) if raw_model else None
    
    raw_provider = attrs.get("gen_ai.provider.name")
    provider = normalize_provider(raw_provider) if raw_provider else None
    
    # Timing
    start_time = datetime.fromtimestamp(span.start_time_ns / 1_000_000_000, tz=timezone.utc)
    end_time = datetime.fromtimestamp(span.end_time_ns / 1_000_000_000, tz=timezone.utc)
    # latency_ms is computed automatically by the database
    
    # Tokens
    tokens_in = attrs.get("gen_ai.usage.input_tokens")
    tokens_out = attrs.get("gen_ai.usage.output_tokens")
    
    # Cost calculation
    input_cost_usd = None
    output_cost_usd = None
    total_cost_usd = None
    
    try:
        from dakora_server.core.token_pricing import get_pricing_service
        
        if provider and model and (tokens_in is not None or tokens_out is not None):
            pricing_service = get_pricing_service()
            total_cost_usd = pricing_service.calculate_cost(
                provider=provider,
                model=model,
                tokens_in=tokens_in or 0,
                tokens_out=tokens_out or 0,
            )
            # For now, store total cost only
            # Could split into input/output if pricing service provides it
    except Exception as e:
        logger.debug(f"Cost calculation failed for span {span.span_id}: {e}")
    
    # Status
    status = span.status_code if span.status_code else "UNSET"
    status_message = span.status_message
    
    # Store all attributes as JSONB
    attributes = span.attributes or {}
    
    execution_data = {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "parent_span_id": parent_span_id,  # May be NULL if parent doesn't exist yet
        "project_id": project_id,
        "type": span_type,
        "span_kind": span.span_kind or None,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "provider": provider,
        "model": model,
        "start_time": start_time,
        "end_time": end_time,
        # latency_ms is computed automatically by the database
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "input_cost_usd": input_cost_usd,
        "output_cost_usd": output_cost_usd,
        "total_cost_usd": total_cost_usd,
        "status": status,
        "status_message": status_message,
        "attributes": attributes,
    }
    
    # Log agent information for debugging
    if agent_id or agent_name:
        logger.info(
            f"Storing execution with agent info - span_id={span.span_id[:8]}, "
            f"agent_id={agent_id}, agent_name={agent_name}, "
            f"parent_span_id={span.parent_span_id[:8] if span.parent_span_id else None}, "
            f"span_name={span.span_name}"
        )
    
    # Use upsert to handle potential duplicates
    stmt = insert(executions_new_table).values(**execution_data).on_conflict_do_update(
        index_elements=['trace_id', 'span_id'],
        set_=execution_data
    )
    conn.execute(stmt)


def _determine_span_type(span: OTLPSpan) -> str:
    """Determine execution type from span attributes and name.
    
    Pattern matching order: most specific to most general.
    Returns 'unknown' for unrecognized patterns to aid discovery.
    """
    span_name = span.span_name.lower()
    
    # Workflow operations (most specific)
    if span_name.startswith("workflow."):
        return "workflow_build" if "build" in span_name else "workflow_run"
    
    # Framework-specific operations (by prefix for efficiency)
    if span_name.startswith("executor."):
        return "executor_process"
    
    if span_name.startswith("edge_group."):
        return "edge_group_process"
    
    if span_name.startswith("message."):
        return "message_send"
    
    # Agent operations (check invoke_agent first as it's more specific)
    if "invoke_agent" in span_name:
        return "agent"
    
    # LLM operations (substring matching)
    if "chat" in span_name:
        return "chat"
    
    if "tool" in span_name or "execute_tool" in span_name:
        return "tool"
    
    if "llm" in span_name:
        return "llm"
    
    # Generic agent catch-all (after more specific checks)
    if "agent" in span_name:
        return "agent"
    
    # Edge group without prefix (less common pattern)
    if "edge_group" in span_name:
        return "edge_group_process"
    
    # Unknown pattern - log for discovery
    logger.debug(f"Unknown span type for span_name='{span.span_name}'")
    return "unknown"


def _extract_and_store_messages(span: OTLPSpan, conn: Connection) -> None:
    """Extract and store input/output messages from span."""
    import json
    
    attrs = span.attributes or {}
    
    # Extract input messages
    input_messages_json = attrs.get("gen_ai.input.messages")
    if input_messages_json:
        try:
            input_messages = json.loads(input_messages_json)
            for idx, msg in enumerate(input_messages):
                _store_message(span, "input", idx, msg, conn)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse input messages for span {span.span_id}: {e}")
    
    # Extract output messages
    output_messages_json = attrs.get("gen_ai.output.messages")
    if output_messages_json:
        try:
            output_messages = json.loads(output_messages_json)
            for idx, msg in enumerate(output_messages):
                _store_message(span, "output", idx, msg, conn)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse output messages for span {span.span_id}: {e}")


def _store_message(
    span: OTLPSpan,
    direction: str,
    msg_index: int,
    msg: dict[str, Any],
    conn: Connection,
) -> None:
    """Store a single message."""
    role = msg.get("role", "user")
    
    # Parse parts (handle both text content and parts array)
    parts = []
    if msg.get("parts"):
        # Already in parts format
        parts = msg["parts"]
    elif msg.get("content"):
        # Convert content to parts format
        parts = [{"type": "text", "content": msg["content"]}]
    
    finish_reason = msg.get("finish_reason")
    
    message_data = {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "direction": direction,
        "msg_index": msg_index,
        "role": role,
        "parts": parts,
        "finish_reason": finish_reason,
    }
    
    # Use insert with on_conflict to handle duplicates
    stmt = insert(execution_messages_new_table).values(**message_data).on_conflict_do_nothing(
        index_elements=['trace_id', 'span_id', 'direction', 'msg_index']
    )
    conn.execute(stmt)


def _extract_and_store_tools(span: OTLPSpan, conn: Connection) -> None:
    """Extract and store tool invocations from span."""
    import json
    from datetime import datetime, timezone
    
    attrs = span.attributes or {}
    
    # Check for tool calls in output messages
    output_messages_json = attrs.get("gen_ai.output.messages")
    if not output_messages_json:
        return
    
    try:
        output_messages = json.loads(output_messages_json)
        for msg in output_messages:
            # Look for tool calls in message
            if msg.get("role") == "assistant" and msg.get("parts"):
                for part in msg["parts"]:
                    if isinstance(part, dict) and part.get("type") == "function_call":
                        # Extract tool call details
                        tool_call_id = part.get("id") or f"{span.span_id}_tool_{part.get('name')}"
                        tool_name = part.get("name")
                        tool_input = part.get("args") or part.get("arguments")
                        
                        # Look for corresponding tool response
                        tool_output = None
                        for resp_msg in output_messages:
                            if resp_msg.get("role") == "tool" and resp_msg.get("parts"):
                                for resp_part in resp_msg["parts"]:
                                    if isinstance(resp_part, dict) and resp_part.get("type") == "function_response":
                                        if resp_part.get("id") == tool_call_id or resp_part.get("name") == tool_name:
                                            tool_output = resp_part.get("response")
                        
                        # Store tool invocation
                        tool_data = {
                            "trace_id": span.trace_id,
                            "span_id": span.span_id,
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                            "tool_output": tool_output,
                            "start_time": datetime.fromtimestamp(span.start_time_ns / 1_000_000_000, tz=timezone.utc),
                            "end_time": datetime.fromtimestamp(span.end_time_ns / 1_000_000_000, tz=timezone.utc),
                            # latency_ms is computed automatically by the database
                            "status": "ok" if tool_output else None,
                            "error_message": None,
                        }
                        
                        stmt = insert(tool_invocations_new_table).values(**tool_data).on_conflict_do_nothing(
                            index_elements=['trace_id', 'tool_call_id']
                        )
                        conn.execute(stmt)
                        
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug(f"Failed to parse tool calls for span {span.span_id}: {e}")