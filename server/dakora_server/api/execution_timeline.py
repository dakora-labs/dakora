"""API endpoint for normalized execution timeline (chat + tools)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

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
)


router = APIRouter()


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
    import hashlib
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

    def extract_text_from_parts(parts: list[dict]) -> str:
        if not parts:
            return ""
        texts: list[str] = []
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                content = p.get("content")
                if isinstance(content, str) and content.strip():
                    # Strip dakora metadata comment fragments from content
                    sanitized = re.sub(r"<!--\s*dakora:[^>]*-->", "", content, flags=re.IGNORECASE)
                    sanitized = sanitized.strip()
                    if sanitized:
                        texts.append(sanitized)
        return "\n\n".join(texts).strip()

    events: list[dict[str, Any]] = []

    with get_connection(engine) as conn:
        # Determine the first span that contains input messages (prefer chat; fallback to any span)
        first_input = conn.execute(
            select(
                executions_table.c.span_id,
                executions_table.c.start_time,
            )
            .select_from(
                executions_table.join(
                    execution_messages_table,
                    and_(
                        executions_table.c.trace_id == execution_messages_table.c.trace_id,
                        executions_table.c.span_id == execution_messages_table.c.span_id,
                    ),
                )
            )
            .where(
                and_(
                    executions_table.c.project_id == project_id,
                    executions_table.c.trace_id == trace_id,
                    execution_messages_table.c.direction == "input",
                )
            )
            .order_by(executions_table.c.start_time)
            .limit(1)
        ).fetchone()

        # If there are no messages at all, return empty events
        if not first_input:
            return TimelineResponse(events=[])

        first_input_span_id = first_input.span_id
        first_input_start = first_input.start_time

        # 1) Inputs from the first input span only
        input_rows = conn.execute(
            select(
                execution_messages_table.c.role,
                execution_messages_table.c.parts,
                execution_messages_table.c.msg_index,
            )
            .where(
                and_(
                    execution_messages_table.c.trace_id == trace_id,
                    execution_messages_table.c.span_id == first_input_span_id,
                    execution_messages_table.c.direction == "input",
                )
            )
            .order_by(execution_messages_table.c.msg_index)
        ).fetchall()

        for u_idx, row in enumerate(input_rows):
            const_text = extract_text_from_parts(row.parts)
            if not const_text:
                continue
            ev = TimelineUserEvent(ts=iso(first_input_start), text=const_text, role=row.role, lane=None).model_dump()
            ev["_order"] = -100000 + u_idx
            events.append(ev)

        # 2) Assistant messages from all spans (not just chat), ordered by span start and msg_index
        output_rows = conn.execute(
            select(
                execution_messages_table.c.role,
                execution_messages_table.c.parts,
                execution_messages_table.c.msg_index,
                execution_messages_table.c.span_id,
                executions_table.c.start_time,
                executions_table.c.latency_ms,
                executions_table.c.tokens_out,
                executions_table.c.agent_name,
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
                    execution_messages_table.c.direction == "output",
                )
            )
            .order_by(executions_table.c.start_time, execution_messages_table.c.msg_index)
        ).fetchall()

        # Build a span -> agent map from outputs for lane labels and a stable row order index
        span_agent: dict[str, str | None] = {}
        row_seq: dict[tuple[str, int, str], int] = {}
        for idx, r in enumerate(output_rows):
            if r.span_id not in span_agent:
                span_agent[r.span_id] = r.agent_name
            role_key = (r.role or "").lower()
            row_seq[(r.span_id, r.msg_index, role_key)] = idx

        seen_text_hashes: set[str] = set()
        for idx, row in enumerate(output_rows):
            if (row.role or "").lower() == "tool":
                continue
            text = extract_text_from_parts(row.parts)
            if not text:
                continue
            h = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
            if h in seen_text_hashes:
                continue
            seen_text_hashes.add(h)
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
            events.append(ev)

        # 3) Tool calls and results from normalized table
        # Reflect actual table schema at runtime to avoid referencing missing columns
        try:
            tool_inv_rt = Table('tool_invocations', MetaData(), autoload_with=conn)
            tool_cols = {c.name for c in tool_inv_rt.c}
        except Exception as e:
            logger.warning(f"Failed to load tool_invocations table schema: {e}. Skipping tool events.")
            tool_rows = []
            tool_inv_rt = None
            tool_cols = set()

        # Decide which IO columns exist
        has_args_result = bool({'arguments', 'result'}.issubset(tool_cols)) if tool_cols else False
        has_tool_io = bool({'tool_input', 'tool_output'}.issubset(tool_cols)) if tool_cols else False

        # Build select columns dynamically and alias to a consistent shape
        if tool_inv_rt is not None:
            base_cols = [
                tool_inv_rt.c.tool_call_id,
                tool_inv_rt.c.tool_name,
                tool_inv_rt.c.start_time,
                tool_inv_rt.c.end_time,
                tool_inv_rt.c.span_id,
            ]

            if has_args_result:
                cols = base_cols + [
                    tool_inv_rt.c.arguments.label('arguments'),
                    tool_inv_rt.c.result.label('result'),
                ]
            elif has_tool_io:
                cols = base_cols + [
                    tool_inv_rt.c.tool_input.label('arguments'),
                    tool_inv_rt.c.tool_output.label('result'),
                ]
            else:
                cols = base_cols

            tool_rows = conn.execute(
                select(*cols)
                .where(tool_inv_rt.c.trace_id == trace_id)
                .order_by(tool_inv_rt.c.start_time)
            ).fetchall()
        else:
            tool_rows = []

        # Track tool_call_ids we already emitted to avoid duplicates when we synthesize from messages
        emitted_tool_ids: set[str] = set()

        # Prepare to synthesize and order tool events consistently
        emitted_tool_ids: set[str] = set()
        tool_events: list[dict[str, Any]] = []

        for row in tool_rows:
            lane = None
            if row.span_id:
                lane = span_agent.get(row.span_id) or row.span_id

            call_ev = TimelineToolCallEvent(
                ts=iso(row.start_time),
                tool_call_id=row.tool_call_id,
                name=row.tool_name,
                arguments=(getattr(row, 'arguments', None)),
                span_id=row.span_id,
                lane=lane,
            ).model_dump()
            result_ev = TimelineToolResultEvent(
                ts=iso(row.end_time or row.start_time),
                tool_call_id=row.tool_call_id,
                output=(getattr(row, 'result', None)),
                ok=True if (hasattr(row, 'result') and getattr(row, 'result') is not None) else None,
                span_id=row.span_id,
                lane=lane,
            ).model_dump()
            # Derive order from nearest output message index by timestamp
            def nearest_idx(ts):
                if not output_rows:
                    return 0
                for i, r in enumerate(output_rows):
                    if r.start_time and ts and r.start_time >= ts:
                        return i
                return len(output_rows)

            idx_call = nearest_idx(row.start_time)
            idx_res = nearest_idx(row.end_time or row.start_time)
            call_ev["_order"] = idx_call * 10 + 1
            result_ev["_order"] = idx_res * 10 + 2
            tool_events.append(call_ev)
            tool_events.append(result_ev)
            emitted_tool_ids.add(row.tool_call_id)

        # 3b) Synthesize tool events from execution_messages when not present in table
        # Look for function_call and function_response parts in output_rows
        # We will emit events only for tool_call_ids not already emitted
        def _lane_for_span(sid: str | None) -> str | None:
            if not sid:
                return None
            return span_agent.get(sid) or sid

        # First pass: collect calls
        calls: dict[str, dict[str, Any]] = {}
        for r in output_rows:
            if not r.parts:
                continue
            # function_call is embedded in assistant messages
            if (r.role or "").lower() == "assistant":
                for part in r.parts or []:
                    if isinstance(part, dict) and part.get("type") in ("function_call", "tool_call"):
                        call_id = part.get("id") or f"{r.span_id}_tool_{part.get('name')}"
                        if not call_id:
                            continue
                        if call_id in emitted_tool_ids:
                            continue
                        idx = row_seq.get((r.span_id, r.msg_index, "assistant"), 0)
                        calls.setdefault(call_id, {})
                        calls[call_id].update({
                            "name": part.get("name"),
                            "arguments": part.get("args") or part.get("arguments"),
                            "span_id": r.span_id,
                            "ts": r.start_time,
                            "order_call": idx,
                        })
        # Second pass: match responses
        for r in output_rows:
            if not r.parts:
                continue
            if (r.role or "").lower() == "tool":
                for part in r.parts or []:
                    if isinstance(part, dict) and part.get("type") in ("function_response", "tool_call_response"):
                        call_id = part.get("id") or None
                        name = part.get("name")
                        if not call_id:
                            # try join by name if id missing
                            for cid, data in calls.items():
                                if data.get("name") == name:
                                    call_id = cid
                                    break
                        if not call_id:
                            continue
                        idx = row_seq.get((r.span_id, r.msg_index, "tool"), 0)
                        entry = calls.setdefault(call_id, {})
                        entry.update({
                            "result": part.get("response"),
                            "span_id": entry.get("span_id") or r.span_id,
                            "ts_result": r.start_time,
                            "order_result": idx,
                        })

        # Emit synthesized events
        for cid, data in calls.items():
            if cid in emitted_tool_ids:
                continue
            lane = _lane_for_span(data.get("span_id"))
            base_order = min(data.get("order_call", 10**9), data.get("order_result", 10**9))
            call_ev = TimelineToolCallEvent(
                ts=iso(data.get("ts")),
                tool_call_id=cid,
                name=data.get("name"),
                arguments=data.get("arguments"),
                span_id=data.get("span_id"),
                lane=lane,
            ).model_dump()
            result_ev = TimelineToolResultEvent(
                ts=iso(data.get("ts_result") or data.get("ts")),
                tool_call_id=cid,
                output=data.get("result"),
                ok=True if data.get("result") is not None else None,
                span_id=data.get("span_id"),
                lane=lane,
            ).model_dump()
            call_ev["_order"] = base_order * 10 + 1
            result_ev["_order"] = base_order * 10 + 2
            tool_events.append(call_ev)
            tool_events.append(result_ev)

        # Merge tool events into main list
        events.extend(tool_events)

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
                    new_ev = {
                        "kind": "tool",
                        "ts": res.get("ts") or ev.get("ts"),
                        "tool_call_id": cid,
                        "name": ev.get("name"),
                        "arguments": ev.get("arguments"),
                        "output": res.get("output"),
                        "ok": res.get("ok"),
                        "span_id": ev.get("span_id") or res.get("span_id"),
                        "lane": ev.get("lane") or res.get("lane"),
                        "_order": min(ev.get("_order", 10**9), res.get("_order", 10**9)),
                    }
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
                    new_ev = {
                        "kind": "tool",
                        "ts": ev.get("ts") or call.get("ts"),
                        "tool_call_id": cid,
                        "name": call.get("name"),
                        "arguments": call.get("arguments"),
                        "output": ev.get("output"),
                        "ok": ev.get("ok"),
                        "span_id": call.get("span_id") or ev.get("span_id"),
                        "lane": call.get("lane") or ev.get("lane"),
                        "_order": min(call.get("_order", 10**9), ev.get("_order", 10**9)),
                    }
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
