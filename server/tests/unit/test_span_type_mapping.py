"""Unit tests for span type determination in otlp_processor."""

from __future__ import annotations

from dakora_server.api.otlp_traces import OTLPSpan
from dakora_server.core.otlp_processor import _determine_span_type


def _span(name: str) -> OTLPSpan:
    return OTLPSpan(
        trace_id="t",
        span_id="s",
        parent_span_id=None,
        span_name=name,
        span_kind="INTERNAL",
        attributes={"gen_ai.operation.name": "noop"},
        events=[],
        start_time_ns=1,
        end_time_ns=2,
        status_code=None,
        status_message=None,
    )


def test_span_type_mapping_various_names():
    assert _determine_span_type(_span("workflow.run")) in {"workflow_run", "workflow_build"}
    assert _determine_span_type(_span("workflow.build")) in {"workflow_run", "workflow_build"}
    assert _determine_span_type(_span("executor.process")) == "executor_process"
    assert _determine_span_type(_span("edge_group.process")) == "edge_group_process"
    assert _determine_span_type(_span("message.send")) == "message_send"
    assert _determine_span_type(_span("invoke_agent something")) == "agent"
    assert _determine_span_type(_span("chat do")) == "chat"
    assert _determine_span_type(_span("tool execute")) == "tool"
    assert _determine_span_type(_span("llm inference")) == "llm"
    assert _determine_span_type(_span("agent orchestrate")) == "agent"
    assert _determine_span_type(_span("unknown_name")) == "unknown"

