"""Integration-level tests for otlp_processor with the database.

Exercises fast-path extraction, recompute path, message extraction,
and tool invocation extraction into normalized schema tables.
"""

from __future__ import annotations

import json
from uuid import uuid4
import pytest

from dakora_server.api.otlp_traces import OTLPSpan
from dakora_server.core.otlp_processor import process_trace_batch
from dakora_server.core.database import (
    traces_table,
    executions_table,
    execution_messages_table,
    tool_invocations_table,
)
from sqlalchemy import select


def _mk_span(
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    name: str,
    attrs: dict,
    start_ns: int = 1_000_000_000,
    end_ns: int = 2_000_000_000,
    status: str | None = "OK",
):
    return OTLPSpan(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        span_name=name,
        span_kind="INTERNAL",
        attributes=attrs,
        events=[],
        start_time_ns=start_ns,
        end_time_ns=end_ns,
        status_code=status,
        status_message=None,
    )


def test_fast_path_creates_trace_execution_and_messages(db_connection, test_project):
    project_id, _, _ = test_project
    # OTLP expects 32-char hex trace IDs
    trace_id = uuid4().hex

    attrs = {
        "gen_ai.operation.name": "chat",
        "gen_ai.agent.id": "agent-1",
        "gen_ai.agent.name": "Agent One",
        "gen_ai.request.model": "gpt-4o-mini-2024-07-18",
        "gen_ai.provider.name": "azure.ai.openai",
        "gen_ai.usage.input_tokens": 12,
        "gen_ai.usage.output_tokens": 34,
        "gen_ai.input.messages": json.dumps([
            {"role": "user", "parts": [{"type": "text", "content": "Hi"}]}
        ]),
        "gen_ai.output.messages": json.dumps([
            {"role": "assistant", "parts": [{"type": "text", "content": "Hello"}]}
        ]),
        # Included to populate traces.provider via _upsert_trace_record
        "dakora.span_source": "otlp-test",
    }
    span_id = uuid4().hex[:16]
    span = _mk_span(trace_id, span_id, None, "chat gpt-4o-mini", attrs)

    stats = process_trace_batch([span], project_id, db_connection)
    assert stats["spans_stored"] == 1
    assert stats["executions_created"] == 1  # root chat span
    assert stats["recomputes"] == 0

    # Verify trace row
    row = db_connection.execute(
        select(traces_table).where(traces_table.c.trace_id == trace_id)
    ).fetchone()
    assert row is not None
    assert str(row.project_id) == str(project_id)
    assert row.provider == "otlp-test"

    # Verify execution row
    exec_row = db_connection.execute(
        select(executions_table).where(
            executions_table.c.trace_id == trace_id,
            executions_table.c.span_id == span_id,
        )
    ).fetchone()
    assert exec_row is not None
    assert exec_row.type == "chat"
    assert exec_row.agent_id == "agent-1"
    # Normalized
    assert exec_row.provider == "azure_openai"
    assert exec_row.model == "gpt-4o-mini"
    assert exec_row.tokens_in == 12
    assert exec_row.tokens_out == 34
    assert exec_row.status == "OK"

    # Verify messages stored (both directions)
    msgs = db_connection.execute(
        select(execution_messages_table).where(
            execution_messages_table.c.trace_id == trace_id,
            execution_messages_table.c.span_id == span_id,
        )
    ).fetchall()
    assert len(msgs) == 2
    
    # Cleanup inserted rows for this trace
    from sqlalchemy import delete
    from dakora_server.core.database import otel_spans_table
    db_connection.execute(delete(execution_messages_table).where(execution_messages_table.c.trace_id == trace_id))
    db_connection.execute(delete(executions_table).where(executions_table.c.trace_id == trace_id))
    db_connection.execute(delete(tool_invocations_table).where(tool_invocations_table.c.trace_id == trace_id))
    db_connection.execute(delete(otel_spans_table).where(otel_spans_table.c.trace_id == trace_id))
    db_connection.execute(delete(traces_table).where(traces_table.c.trace_id == trace_id))
    db_connection.commit()


def test_recompute_links_parent_and_extracts_tools(db_connection, test_project):
    project_id, _, _ = test_project
    trace_id = uuid4().hex

    # Skip if the DB schema doesn't have tool_invocations columns we rely on
    from sqlalchemy import inspect
    insp = inspect(db_connection)
    try:
        cols = {c["name"] for c in insp.get_columns("tool_invocations")}
    except Exception:
        cols = set()
    required = {"tool_call_id", "tool_name", "tool_input", "tool_output"}
    # If minimal columns are missing, skip this test to avoid schema mismatch
    if not required.issubset(cols):
        pytest.skip("tool_invocations table missing required columns; skipping tool extraction test")

    # Child span arrives first (parent missing) with tool call
    tool_call_id = "call-123"
    child_attrs = {
        "gen_ai.operation.name": "chat",
        "gen_ai.request.model": "gpt-4o-mini",
        "gen_ai.provider.name": "openai",
        "gen_ai.output.messages": json.dumps([
            {
                "role": "assistant",
                "parts": [
                    {"type": "function_call", "id": tool_call_id, "name": "lookup", "args": {"q": "x"}}
                ],
            },
            {
                "role": "tool",
                "parts": [
                    {"type": "function_response", "id": tool_call_id, "name": "lookup", "response": {"ok": True}}
                ],
            },
        ]),
    }
    parent_id = uuid4().hex[:16]
    child_id = uuid4().hex[:16]
    child = _mk_span(trace_id, child_id, parent_id, "chat", child_attrs)

    stats1 = process_trace_batch([child], project_id, db_connection)
    assert stats1["spans_stored"] == 1
    assert stats1["executions_created"] == 0  # child only, not root
    assert stats1["recomputes"] == 0

    # Now parent span arrives, same trace → recompute path
    parent_attrs = {"gen_ai.operation.name": "invoke_agent"}
    parent = _mk_span(trace_id, parent_id, None, "invoke_agent orchestrator", parent_attrs)

    stats2 = process_trace_batch([parent], project_id, db_connection)
    assert stats2["spans_stored"] == 1
    assert stats2["recomputes"] == 1

    # After recompute, child should link to parent
    child_row = db_connection.execute(
        select(executions_table).where(
            executions_table.c.trace_id == trace_id,
            executions_table.c.span_id == child_id,
        )
    ).fetchone()
    assert child_row is not None
    assert child_row.parent_span_id == parent_id

    # Tool invocation should be extracted
    tool = db_connection.execute(
        select(tool_invocations_table).where(
            tool_invocations_table.c.trace_id == trace_id,
            tool_invocations_table.c.tool_call_id == tool_call_id,
        )
    ).fetchone()
    assert tool is not None
    assert tool.tool_name == "lookup"
    
    # Cleanup inserted rows for this trace
    from sqlalchemy import delete
    from dakora_server.core.database import otel_spans_table
    db_connection.execute(delete(execution_messages_table).where(execution_messages_table.c.trace_id == trace_id))
    db_connection.execute(delete(tool_invocations_table).where(tool_invocations_table.c.trace_id == trace_id))
    db_connection.execute(delete(executions_table).where(executions_table.c.trace_id == trace_id))
    db_connection.execute(delete(otel_spans_table).where(otel_spans_table.c.trace_id == trace_id))
    db_connection.execute(delete(traces_table).where(traces_table.c.trace_id == trace_id))
    db_connection.commit()
