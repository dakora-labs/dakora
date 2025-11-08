"""API endpoint for normalized execution timeline (chat + tools)."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from collections import defaultdict
from bisect import bisect_left

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, MetaData, Table
from sqlalchemy.engine import Engine

from dakora_server.auth import validate_project_access
from dakora_server.core.database import (
    get_engine,
    get_connection,
    executions_table,
    execution_messages_table,
)
from dakora_server.api.schemas import (
    TimelineResponse,
    TimelineUserEvent,
    TimelineAssistantEvent,
    TimelineToolCallEvent,
    TimelineToolResultEvent,
    TimelineToolCompositeEvent,
)


router = APIRouter()

# Cached reflection for tool_invocations to avoid per-request information_schema hits
_TOOL_TABLE = None
_TOOL_COLS: set[str] | None = None


@router.get("/api/projects/{project_id}/executions/{trace_id}/timeline")
async def get_execution_timeline(
    project_id: UUID,
    trace_id: str,
    compact_tools: bool = Query(False, description="If true, collapse tool_call+tool_result pairs into a single tool event"),
    _: UUID = Depends(validate_project_access),
    engine: Engine = Depends(get_engine),
) -> TimelineResponse:
    """Return a simplified, deduplicated, ordered timeline for a trace.

    The timeline emphasizes chat turns and tool calls/results with minimal
    debug detail. Events are normalized so the UI can render them directly.
    
    Args:
        project_id: Project UUID (validated via auth dependency)
        trace_id: Execution trace ID (validated for format)
        compact_tools: If true, merges tool_call+tool_result into single tool event
        
    Returns:
        TimelineResponse with normalized events ordered by timestamp
        
    Raises:
        HTTPException: 400 if trace_id is invalid; 404 if trace not found or not accessible
    """
    from datetime import timezone
    import re
    import logging
    from fastapi import HTTPException
    
    logger = logging.getLogger(__name__)
    
    # Input validation
    if not trace_id or not isinstance(trace_id, str):
        raise HTTPException(status_code=400, detail="trace_id must be a non-empty string")
    if len(trace_id) > 256:
        raise HTTPException(status_code=400, detail="trace_id exceeds maximum length of 256 characters")
    
    # Basic format validation (alphanumeric, hyphens, underscores)
    if not all(c.isalnum() or c in '-_' for c in trace_id):
        raise HTTPException(status_code=400, detail="trace_id contains invalid characters")

    def iso(dt) -> str:
        return dt.astimezone(timezone.utc).isoformat() if dt else ""

    # Precompile sanitizer regex once per request
    re_dakora = re.compile(r"<!--\s*dakora:[^>]*-->", re.IGNORECASE)

    def extract_text_from_parts(parts: list[dict]) -> str:
        if not parts:
            return ""
        texts: list[str] = []
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                content = p.get("content")
                if isinstance(content, str) and content.strip():
                    # Strip dakora metadata comment fragments from content
                    sanitized = re_dakora.sub("", content)
                    sanitized = sanitized.strip()
                    if sanitized:
                        texts.append(sanitized)
        return "\n\n".join(texts).strip()

    events: list[dict[str, Any]] = []

    with get_connection(engine) as conn:
        # Single pass: fetch all messages (both directions) for the trace
        message_rows = conn.execute(
            select(
                execution_messages_table.c.direction,
                execution_messages_table.c.role,
                execution_messages_table.c.parts,
                execution_messages_table.c.msg_index,
                execution_messages_table.c.span_id,
                executions_table.c.start_time,
                executions_table.c.latency_ms,
                executions_table.c.tokens_out,
                executions_table.c.agent_name,
                executions_table.c.parent_span_id,
            )
            .select_from(
                execution_messages_table.join(
                    executions_table,
                    and_(
                        execution_messages_table.c.trace_id == executions_table.c.trace_id,
                        execution_messages_table.c.span_id == executions_table.c.span_id,
                    ),
                )
            )
            .where(
                and_(
                    execution_messages_table.c.trace_id == trace_id,
                    executions_table.c.project_id == project_id,
                )
            )
            .order_by(executions_table.c.start_time, execution_messages_table.c.msg_index)
        ).fetchall()

        if not message_rows:
            return TimelineResponse(events=[])

        # Determine first input span and emit its user messages
        first_input_span_id = None
        first_input_start = None
        for row in message_rows:
            if (row.direction or "").lower() == "input":
                first_input_span_id = row.span_id
                first_input_start = row.start_time
                break

        if first_input_span_id is None or first_input_start is None:
            return TimelineResponse(events=[])

        first_input_msgs = [
            r for r in message_rows
            if (r.direction or "").lower() == "input" and r.span_id == first_input_span_id
        ]
        first_input_msgs.sort(key=lambda r: r.msg_index)
        for u_idx, row in enumerate(first_input_msgs):
            const_text = extract_text_from_parts(row.parts)
            if not const_text:
                continue
            ev = TimelineUserEvent(ts=iso(first_input_start), text=const_text, role=row.role, lane=None).model_dump()
            ev["_order"] = -100000 + u_idx
            events.append(ev)

        # Outputs for assistant/tool processing
        output_rows = [r for r in message_rows if (r.direction or "").lower() == "output"]

        # Build a span -> agent map from outputs for lane labels and a stable row order index
        span_agent: dict[str, str | None] = {}
        row_seq: dict[tuple[str, int, str], int] = {}
        for idx, r in enumerate(output_rows):
            if r.span_id not in span_agent:
                span_agent[r.span_id] = r.agent_name
            role_key = (r.role or "").lower()
            row_seq[(r.span_id, r.msg_index, role_key)] = idx

        assistant_candidates: dict[
            tuple[str, int, str], tuple[tuple[int, int, int], dict[str, Any]]
        ] = {}
        for idx, row in enumerate(output_rows):
            if (row.role or "").lower() == "tool":
                continue
            text = extract_text_from_parts(row.parts)
            if not text:
                continue
            msg_key = ((row.role or "").lower(), row.msg_index, text)
            priority = (
                0 if row.agent_name else 1,
                0 if getattr(row, "parent_span_id", None) is None else 1,
                idx,
            )
            existing = assistant_candidates.get(msg_key)
            ev = TimelineAssistantEvent(
                ts=iso(row.start_time),
                span_id=row.span_id,
                agent_name=row.agent_name,
                text=text,
                tokens_out=row.tokens_out,
                latency_ms=row.latency_ms,
                lane=row.agent_name or row.span_id,
            ).model_dump()
            ev["_order"] = idx * 10 + 8
            ev["_parent_span_id"] = row.parent_span_id
            if existing is None or priority < existing[0]:
                assistant_candidates[msg_key] = (priority, ev)

        for _, (_, ev) in assistant_candidates.items():
            events.append(ev)

        # 3) Tool calls and results from normalized table (handle legacy/new schemas at runtime)
        # Short-circuit: if no tool evidence in messages, skip DB query
        tool_evidence = False
        for r in output_rows:
            if not r.parts:
                continue
            role = (r.role or "").lower()
            if role == "assistant":
                for part in r.parts:
                    if isinstance(part, dict) and part.get("type") in ("function_call", "tool_call"):
                        tool_evidence = True
                        break
            elif role == "tool":
                for part in r.parts:
                    if isinstance(part, dict) and part.get("type") in ("function_response", "tool_call_response"):
                        tool_evidence = True
                        break
            if tool_evidence:
                break

        if tool_evidence:
            # Cache reflection to avoid per-request information_schema queries
            global _TOOL_TABLE, _TOOL_COLS
            tool_inv_rt = _TOOL_TABLE
            tool_cols = _TOOL_COLS or set()
            if tool_inv_rt is None:
                try:
                    tool_inv_rt = Table("tool_invocations", MetaData(), autoload_with=conn)
                    tool_cols = {c.name for c in tool_inv_rt.c}
                    _TOOL_TABLE = tool_inv_rt
                    _TOOL_COLS = tool_cols
                except Exception as exc:
                    logger.warning("Failed to reflect tool_invocations table: %s", exc)
                    tool_inv_rt = None
                    tool_cols = set()

            if tool_inv_rt is not None:
                base_cols = [
                    tool_inv_rt.c.tool_call_id,
                    tool_inv_rt.c.tool_name,
                    tool_inv_rt.c.start_time,
                    tool_inv_rt.c.end_time,
                    tool_inv_rt.c.span_id,
                ]
                arguments_col = None
                if "arguments" in tool_cols:
                    arguments_col = tool_inv_rt.c.arguments.label("arguments")
                elif "tool_input" in tool_cols:
                    arguments_col = tool_inv_rt.c.tool_input.label("arguments")

                result_col = None
                if "result" in tool_cols:
                    result_col = tool_inv_rt.c.result.label("result")
                elif "tool_output" in tool_cols:
                    result_col = tool_inv_rt.c.tool_output.label("result")

                select_cols = list(base_cols)
                if arguments_col is not None:
                    select_cols.append(arguments_col)
                if result_col is not None:
                    select_cols.append(result_col)

                tool_rows = conn.execute(
                    select(*select_cols)
                    .where(tool_inv_rt.c.trace_id == trace_id)
                    .order_by(tool_inv_rt.c.start_time)
                ).fetchall()
            else:
                tool_rows = []
        else:
            tool_rows = []

        def _lane_for_span(sid: str | None) -> str | None:
            if not sid:
                return None
            return span_agent.get(sid) or sid

        # Precompute start times + original indices for binary search placement of tool events
        time_index_pairs = [(r.start_time, i) for i, r in enumerate(output_rows) if r.start_time is not None]
        times = [t for t, _ in time_index_pairs]
        indices = [i for _, i in time_index_pairs]

        def nearest_idx(ts):
            if not times or ts is None:
                return len(output_rows)
            pos = bisect_left(times, ts)
            if pos >= len(indices):
                return len(output_rows)
            return indices[pos]

        tool_records: dict[str, dict[str, Any]] = {}

        for row in tool_rows:
            lane = _lane_for_span(row.span_id)
            rec = tool_records.setdefault(row.tool_call_id, {})
            rec.setdefault("name", row.tool_name)
            if rec.get("arguments") is None:
                rec["arguments"] = getattr(row, "arguments", None)
            if rec.get("result") is None and hasattr(row, "result"):
                rec["result"] = getattr(row, "result")
            rec.setdefault("span_id", row.span_id)
            rec.setdefault("lane", lane)
            rec.setdefault("ts_call", row.start_time)
            rec.setdefault("ts_result", row.end_time or row.start_time)
            idx_call = nearest_idx(row.start_time)
            idx_res = nearest_idx(row.end_time or row.start_time)
            order_call = idx_call * 10 + 1
            order_result = idx_res * 10 + 2
            rec["order_call"] = min(rec.get("order_call", order_call), order_call)
            rec["order_result"] = min(rec.get("order_result", order_result), order_result)

        # Supplement tool data from execution_messages (function call/response parts)
        for r in output_rows:
            if not r.parts:
                continue
            role = (r.role or "").lower()
            if role == "assistant":
                for part in r.parts or []:
                    if isinstance(part, dict) and part.get("type") in ("function_call", "tool_call"):
                        call_id = part.get("id") or f"{r.span_id}_tool_{part.get('name')}"
                        if not call_id:
                            continue
                        rec = tool_records.setdefault(call_id, {})
                        if not rec.get("name"):
                            rec["name"] = part.get("name")
                        if rec.get("arguments") is None:
                            rec["arguments"] = part.get("args") or part.get("arguments")
                        rec.setdefault("span_id", r.span_id)
                        rec.setdefault("lane", _lane_for_span(r.span_id))
                        rec.setdefault("ts_call", r.start_time)
                        idx = row_seq.get((r.span_id, r.msg_index, "assistant"), 0)
                        order_call = idx * 10 + 1
                        rec["order_call"] = min(rec.get("order_call", order_call), order_call)
            elif role == "tool":
                for part in r.parts or []:
                    if isinstance(part, dict) and part.get("type") in ("function_response", "tool_call_response"):
                        call_id = part.get("id")
                        name = part.get("name")
                        if not call_id and name:
                            for cid, data in tool_records.items():
                                if data.get("name") == name:
                                    call_id = cid
                                    break
                        if not call_id:
                            continue
                        rec = tool_records.setdefault(call_id, {})
                        if rec.get("result") is None:
                            rec["result"] = part.get("response")
                        rec.setdefault("span_id", rec.get("span_id") or r.span_id)
                        rec.setdefault("lane", _lane_for_span(rec.get("span_id")))
                        rec.setdefault("ts_result", r.start_time)
                        idx = row_seq.get((r.span_id, r.msg_index, "tool"), 0)
                        order_result = idx * 10 + 2
                        rec["order_result"] = min(rec.get("order_result", order_result), order_result)

        tool_events: list[dict[str, Any]] = []
        for cid, data in tool_records.items():
            lane = data.get("lane")
            call_ev = TimelineToolCallEvent(
                ts=iso(data.get("ts_call")),
                tool_call_id=cid,
                name=data.get("name"),
                arguments=data.get("arguments"),
                span_id=data.get("span_id"),
                lane=lane,
            ).model_dump()
            call_ev["_order"] = data.get("order_call", 10**9)
            tool_events.append(call_ev)

            if data.get("result") is not None or data.get("ts_result") is not None:
                result_ev = TimelineToolResultEvent(
                    ts=iso(data.get("ts_result") or data.get("ts_call")),
                    tool_call_id=cid,
                    output=data.get("result"),
                    ok=True if data.get("result") is not None else None,
                    span_id=data.get("span_id"),
                    lane=lane,
                ).model_dump()
                result_ev["_order"] = data.get("order_result", call_ev["_order"] + 1)
                tool_events.append(result_ev)

        # Merge tool events into main list
        events.extend(tool_events)

    # Remove assistant duplicates that repeat parent text (e.g., agent + underlying chat span)
    seen_text_by_span: dict[str, set[str]] = defaultdict(set)
    deduped_events: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("kind") == "assistant":
            parent_span = ev.pop("_parent_span_id", None)
            text = ev.get("text")
            if parent_span and text and text in seen_text_by_span.get(parent_span, set()):
                continue
            span_id = ev.get("span_id")
            if span_id and text:
                seen_text_by_span.setdefault(span_id, set()).add(text)
        else:
            ev.pop("_parent_span_id", None)
        deduped_events.append(ev)
    events = deduped_events

    # Optionally compact tool call/result pairs into a single event
    if compact_tools:
        pairs: dict[str, dict[str, Any]] = {}
        for ev in events:
            if ev.get("kind") == "tool_call":
                d = pairs.setdefault(ev["tool_call_id"], {})
                d["call"] = ev
            elif ev.get("kind") == "tool_result":
                d = pairs.setdefault(ev["tool_call_id"], {})
                d["result"] = ev
        compacted: list[dict[str, Any]] = []
        emitted: set[str] = set()
        for ev in events:
            k = ev.get("kind")
            if k == "tool_call":
                cid = ev["tool_call_id"]
                pr = pairs.get(cid, {})
                if "result" in pr and cid not in emitted:
                    res = pr["result"]
                    new_ev = TimelineToolCompositeEvent(
                        ts=res.get("ts") or ev.get("ts"),
                        tool_call_id=cid,
                        name=ev.get("name"),
                        arguments=ev.get("arguments"),
                        output=res.get("output"),
                        ok=res.get("ok"),
                        span_id=ev.get("span_id") or res.get("span_id"),
                        lane=ev.get("lane") or res.get("lane"),
                    ).model_dump()
                    new_ev["_order"] = min(ev.get("_order", 10**9), res.get("_order", 10**9))
                    compacted.append(new_ev)
                    emitted.add(cid)
                elif cid in emitted:
                    continue
                else:
                    compacted.append(ev)
            elif k == "tool_result":
                cid = ev["tool_call_id"]
                if cid in emitted:
                    continue
                pr = pairs.get(cid, {})
                if "call" in pr and cid not in emitted:
                    call = pr["call"]
                    new_ev = TimelineToolCompositeEvent(
                        ts=ev.get("ts") or call.get("ts"),
                        tool_call_id=cid,
                        name=call.get("name"),
                        arguments=call.get("arguments"),
                        output=ev.get("output"),
                        ok=ev.get("ok"),
                        span_id=call.get("span_id") or ev.get("span_id"),
                        lane=call.get("lane") or ev.get("lane"),
                    ).model_dump()
                    new_ev["_order"] = min(call.get("_order", 10**9), ev.get("_order", 10**9))
                    compacted.append(new_ev)
                    emitted.add(cid)
                else:
                    compacted.append(ev)
            else:
                compacted.append(ev)
        events = compacted
    # Sort: ts asc, lane, kind precedence
    # Ordering within identical timestamps: user → tool_call → tool_result → assistant
    KIND_WEIGHT = {"user": 0, "tool_call": 1, "tool_result": 2, "assistant": 3, "tool": 1}

    def _key(ev: dict[str, Any]):
        order = ev.get("_order")
        if order is None:
            order = 10**12  # place unsorted items at end by time
        return (order, KIND_WEIGHT.get(ev.get("kind"), 9), ev.get("ts") or "")

    events.sort(key=_key)
    # Strip internal sorting field
    for ev in events:
        if "_order" in ev:
            ev.pop("_order", None)
    return TimelineResponse(events=events)




