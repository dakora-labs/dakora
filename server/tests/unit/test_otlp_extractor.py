"""Unit tests for OTLP extraction logic.

Tests core extraction functionality without database dependencies.
"""

import json
from uuid import uuid4

import pytest

from dakora_server.api.otlp_traces import OTLPSpan
from dakora_server.core.otlp_extractor import (
    build_span_hierarchy,
    extract_conversation_history,
    extract_execution_trace,
    extract_template_usages,
    is_root_execution_span,
    normalize_model,
    normalize_provider,
)


# Fixtures for creating test spans


def create_span(
    trace_id: str = "test-trace-123",
    span_id: str = "span-1",
    parent_span_id: str | None = None,
    span_name: str = "test span",
    operation: str = "invoke_agent",
    attributes: dict | None = None,
    start_ns: int = 1000000000,
    end_ns: int = 2000000000,
) -> OTLPSpan:
    """Create a test OTLP span."""
    attrs = attributes or {}
    if operation:
        attrs["gen_ai.operation.name"] = operation

    return OTLPSpan(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        span_name=span_name,
        span_kind=operation,
        attributes=attrs,
        events=[],
        start_time_ns=start_ns,
        end_time_ns=end_ns,
        status_code=None,
        status_message=None,
    )


# Tests for is_root_execution_span


def test_is_root_execution_span_invoke_agent_no_parent():
    """Root invoke_agent span with no parent should be detected."""
    span = create_span(operation="invoke_agent", parent_span_id=None)
    assert is_root_execution_span(span) is True


def test_is_root_execution_span_chat_no_parent():
    """Root chat span with no parent should be detected."""
    span = create_span(operation="chat", parent_span_id=None)
    assert is_root_execution_span(span) is True


def test_is_root_execution_span_with_parent():
    """Span with parent should NOT be detected as root."""
    span = create_span(operation="invoke_agent", parent_span_id="parent-123")
    assert is_root_execution_span(span) is False


def test_is_root_execution_span_wrong_operation():
    """Span with non-agent operation should NOT be detected."""
    span = create_span(operation="execute_tool", parent_span_id=None)
    assert is_root_execution_span(span) is False


def test_is_root_execution_span_multiple_operation_formats():
    """Should detect various operation name formats."""
    for op in ["invoke_agent", "chat", "agent.invoke", "chat.invoke", "agent_invoke"]:
        span = create_span(operation=op, parent_span_id=None)
        assert is_root_execution_span(span) is True, f"Failed for operation: {op}"


# Tests for normalize_model


def test_normalize_model_strips_date_suffix():
    """Should strip date suffixes from model names."""
    assert normalize_model("gpt-4o-mini-2024-07-18") == "gpt-4o-mini"
    assert normalize_model("gpt-4-2024-01-15") == "gpt-4"
    assert normalize_model("claude-3-opus-2024-02-29") == "claude-3-opus"


def test_normalize_model_preserves_non_date_suffixes():
    """Should preserve model names without date suffixes."""
    assert normalize_model("gpt-4o-mini") == "gpt-4o-mini"
    assert normalize_model("gpt-35-turbo-16k") == "gpt-35-turbo-16k"


def test_normalize_model_unknown():
    """Should return None for 'unknown' model."""
    assert normalize_model("unknown") is None
    assert normalize_model("Unknown") is None
    assert normalize_model("UNKNOWN") is None


def test_normalize_model_none():
    """Should return None for None input."""
    assert normalize_model(None) is None


# Tests for normalize_provider


def test_normalize_provider_azure():
    """Should normalize Azure provider names."""
    assert normalize_provider("azure.ai.openai") == "azure_openai"
    assert normalize_provider("microsoft.agent_framework") == "azure_openai"
    assert normalize_provider("Azure OpenAI") == "azure_openai"


def test_normalize_provider_openai():
    """Should normalize OpenAI provider names."""
    assert normalize_provider("openai") == "openai"
    assert normalize_provider("OpenAI") == "openai"


def test_normalize_provider_anthropic():
    """Should normalize Anthropic provider names."""
    assert normalize_provider("anthropic") == "anthropic"
    assert normalize_provider("claude") == "anthropic"


def test_normalize_provider_google():
    """Should normalize Google provider names."""
    assert normalize_provider("google") == "google"
    assert normalize_provider("gemini") == "google"


def test_normalize_provider_unknown():
    """Should preserve unknown provider names."""
    assert normalize_provider("unknown_provider") == "unknown_provider"


def test_normalize_provider_none():
    """Should return None for None input."""
    assert normalize_provider(None) is None


# Tests for build_span_hierarchy


def test_build_span_hierarchy_simple():
    """Should build hierarchy for parent-child relationship."""
    parent = create_span(span_id="parent", parent_span_id=None)
    child1 = create_span(span_id="child1", parent_span_id="parent")
    child2 = create_span(span_id="child2", parent_span_id="parent")

    hierarchy = build_span_hierarchy([parent, child1, child2])

    assert "parent" in hierarchy
    assert len(hierarchy["parent"]) == 2
    assert child1 in hierarchy["parent"]
    assert child2 in hierarchy["parent"]


def test_build_span_hierarchy_multi_level():
    """Should build hierarchy for multi-level relationships."""
    root = create_span(span_id="root", parent_span_id=None)
    child = create_span(span_id="child", parent_span_id="root")
    grandchild = create_span(span_id="grandchild", parent_span_id="child")

    hierarchy = build_span_hierarchy([root, child, grandchild])

    assert "root" in hierarchy
    assert "child" in hierarchy
    assert len(hierarchy["root"]) == 1
    assert len(hierarchy["child"]) == 1


def test_build_span_hierarchy_no_children():
    """Should handle spans with no children."""
    spans = [create_span(span_id="lonely", parent_span_id=None)]
    hierarchy = build_span_hierarchy(spans)
    assert len(hierarchy) == 0  # No children, empty dict


# Tests for extract_conversation_history


def test_extract_conversation_history_simple():
    """Should extract simple text messages."""
    attrs = {
        "gen_ai.input.messages": json.dumps([
            {"role": "user", "content": "Hello"}
        ]),
        "gen_ai.output.messages": json.dumps([
            {"role": "assistant", "content": "Hi there!"}
        ]),
    }
    span = create_span(attributes=attrs)

    history = extract_conversation_history(span)

    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there!"}


def test_extract_conversation_history_parts_format():
    """Should extract MAF part-based messages."""
    attrs = {
        "gen_ai.input.messages": json.dumps([
            {
                "role": "user",
                "parts": [{"type": "text", "content": "Question 1"}, {"type": "text", "content": "Question 2"}]
            }
        ]),
    }
    span = create_span(attributes=attrs)

    history = extract_conversation_history(span)

    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Question 1\nQuestion 2"


def test_extract_conversation_history_missing_content():
    """Should handle messages without content field."""
    attrs = {
        "gen_ai.input.messages": json.dumps([{"role": "user"}]),
    }
    span = create_span(attributes=attrs)

    history = extract_conversation_history(span)

    assert len(history) == 1
    assert history[0]["content"] == ""


def test_extract_conversation_history_invalid_json():
    """Should handle invalid JSON gracefully."""
    attrs = {
        "gen_ai.input.messages": "invalid json",
    }
    span = create_span(attributes=attrs)

    history = extract_conversation_history(span)

    assert len(history) == 0


def test_extract_conversation_history_empty():
    """Should handle span with no messages."""
    span = create_span(attributes={})

    history = extract_conversation_history(span)

    assert len(history) == 0


# Tests for extract_template_usages


def test_extract_template_usages_from_root():
    """Should extract template contexts from root span."""
    attrs = {
        "dakora.template_contexts": json.dumps([
            {
                "prompt_id": "test-prompt",
                "version": "v1",
                "inputs": {"key": "value"},
                "metadata": {"source": "test"},
                "role": "user"
            }
        ])
    }
    root = create_span(span_id="root", attributes=attrs, parent_span_id=None)
    hierarchy = build_span_hierarchy([root])

    usages = extract_template_usages(root, hierarchy)

    assert len(usages) == 1
    assert usages[0]["prompt_id"] == "test-prompt"
    assert usages[0]["version"] == "v1"
    assert usages[0]["inputs_json"] == {"key": "value"}
    assert usages[0]["metadata_json"] == {"source": "test"}
    assert usages[0]["role"] == "user"


def test_extract_template_usages_from_child():
    """Should extract template contexts from child span."""
    root = create_span(span_id="root", attributes={}, parent_span_id=None)
    child_attrs = {
        "dakora.template_contexts": json.dumps([
            {"prompt_id": "child-prompt", "version": "latest", "inputs": {}}
        ])
    }
    child = create_span(span_id="child", attributes=child_attrs, parent_span_id="root")

    hierarchy = build_span_hierarchy([root, child])
    usages = extract_template_usages(root, hierarchy)

    assert len(usages) == 1
    assert usages[0]["prompt_id"] == "child-prompt"


def test_extract_template_usages_none():
    """Should return None when no templates found."""
    root = create_span(span_id="root", attributes={}, parent_span_id=None)
    hierarchy = build_span_hierarchy([root])

    usages = extract_template_usages(root, hierarchy)

    assert usages is None


def test_extract_template_usages_invalid_json():
    """Should handle invalid template contexts JSON."""
    attrs = {"dakora.template_contexts": "invalid"}
    root = create_span(span_id="root", attributes=attrs, parent_span_id=None)
    hierarchy = build_span_hierarchy([root])

    usages = extract_template_usages(root, hierarchy)

    assert usages is None


# Tests for extract_execution_trace


def test_extract_execution_trace_basic():
    """Should extract basic execution trace from root span."""
    attrs = {
        "gen_ai.agent.id": "test-agent",
        "dakora.session_id": "session-123",
        "dakora.source": "maf",
    }
    root = create_span(
        span_id="root",
        attributes=attrs,
        parent_span_id=None,
        start_ns=1000000000,
        end_ns=2500000000,  # 1500ms duration
    )

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["project_id"] == project_id
    assert trace_data["trace_id"] == "test-trace-123"
    assert trace_data["session_id"] == "session-123"
    assert trace_data["agent_id"] == "test-agent"
    assert trace_data["source"] == "maf"
    assert trace_data["latency_ms"] == 1500


def test_extract_execution_trace_aggregates_from_child():
    """Should aggregate model/provider/tokens from child span."""
    root_attrs = {"gen_ai.agent.id": "agent-1"}
    root = create_span(span_id="root", attributes=root_attrs, parent_span_id=None)

    child_attrs = {
        "dakora.model": "gpt-4o-mini",
        "gen_ai.provider.name": "azure.ai.openai",
        "gen_ai.usage.input_tokens": 100,
        "gen_ai.usage.output_tokens": 50,
    }
    child = create_span(span_id="child", attributes=child_attrs, parent_span_id="root")

    hierarchy = build_span_hierarchy([root, child])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["model"] == "gpt-4o-mini"
    assert trace_data["provider"] == "azure_openai"
    assert trace_data["tokens_in"] == 100
    assert trace_data["tokens_out"] == 50


def test_extract_execution_trace_normalizes_model():
    """Should normalize model names with date suffixes."""
    child_attrs = {
        "gen_ai.response.model": "gpt-4o-mini-2024-07-18",
    }
    root = create_span(span_id="root", parent_span_id=None)
    child = create_span(span_id="child", attributes=child_attrs, parent_span_id="root")

    hierarchy = build_span_hierarchy([root, child])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["model"] == "gpt-4o-mini"


def test_extract_execution_trace_conversation_from_child():
    """Should extract conversation from child span if not in root."""
    root = create_span(span_id="root", parent_span_id=None)

    child_attrs = {
        "gen_ai.input.messages": json.dumps([{"role": "user", "content": "Hello"}]),
        "gen_ai.output.messages": json.dumps([{"role": "assistant", "content": "Hi"}]),
    }
    child = create_span(span_id="child", attributes=child_attrs, parent_span_id="root")

    hierarchy = build_span_hierarchy([root, child])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert len(trace_data["conversation_history"]) == 2
    assert trace_data["conversation_history"][0]["content"] == "Hello"


def test_extract_execution_trace_metadata():
    """Should extract dakora.* metadata attributes."""
    attrs = {
        "dakora.custom_field": "value1",
        "dakora.another_field": "value2",
        "dakora.model": "gpt-4",  # Reserved, should be excluded
        "gen_ai.operation.name": "invoke_agent",  # Not dakora.*, excluded
    }
    root = create_span(span_id="root", attributes=attrs, parent_span_id=None)

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["metadata"] is not None
    assert trace_data["metadata"]["custom_field"] == "value1"
    assert trace_data["metadata"]["another_field"] == "value2"
    assert "model" not in trace_data["metadata"]  # Reserved key


def test_extract_execution_trace_session_id_defaults_to_trace_id():
    """Should use trace_id as session_id when not specified."""
    root = create_span(span_id="root", attributes={}, parent_span_id=None)

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["session_id"] == trace_data["trace_id"]


# Integration test: full flow


def test_full_extraction_flow():
    """Test complete extraction flow with invoke_agent + chat spans."""
    # Create realistic MAF-style spans
    invoke_attrs = {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.id": "haiku-bot",
        "gen_ai.agent.name": "HaikuBot",
        "dakora.session_id": "session-abc",
    }
    invoke_span = create_span(
        trace_id="trace-xyz",
        span_id="invoke-1",
        parent_span_id=None,
        span_name="invoke_agent HaikuBot",
        attributes=invoke_attrs,
        start_ns=1000000000,
        end_ns=3000000000,  # 2000ms
    )

    chat_attrs = {
        "gen_ai.operation.name": "chat",
        "dakora.model": "gpt-4o-mini",
        "gen_ai.provider.name": "azure.ai.openai",
        "gen_ai.response.model": "gpt-4o-mini-2024-07-18",
        "gen_ai.usage.input_tokens": 42,
        "gen_ai.usage.output_tokens": 20,
        "gen_ai.input.messages": json.dumps([
            {"role": "user", "parts": [{"type": "text", "content": "Write a haiku"}]}
        ]),
        "gen_ai.output.messages": json.dumps([
            {"role": "assistant", "parts": [{"type": "text", "content": "Code flows like water"}]}
        ]),
        "dakora.template_contexts": json.dumps([
            {"prompt_id": "haiku_prompt", "version": "latest", "inputs": {}}
        ]),
    }
    chat_span = create_span(
        trace_id="trace-xyz",
        span_id="chat-1",
        parent_span_id="invoke-1",
        span_name="chat gpt-4o-mini",
        attributes=chat_attrs,
    )

    # Verify root detection
    assert is_root_execution_span(invoke_span) is True
    assert is_root_execution_span(chat_span) is False

    # Build hierarchy
    hierarchy = build_span_hierarchy([invoke_span, chat_span])
    assert len(hierarchy["invoke-1"]) == 1

    # Extract execution
    project_id = uuid4()
    trace_data = extract_execution_trace(invoke_span, hierarchy, project_id)

    # Verify aggregation
    assert trace_data["agent_id"] == "haiku-bot"
    assert trace_data["model"] == "gpt-4o-mini"  # Normalized
    assert trace_data["provider"] == "azure_openai"  # Normalized
    assert trace_data["tokens_in"] == 42
    assert trace_data["tokens_out"] == 20
    assert trace_data["latency_ms"] == 2000
    assert len(trace_data["conversation_history"]) == 2

    # Extract templates
    usages = extract_template_usages(invoke_span, hierarchy)
    assert len(usages) == 1
    assert usages[0]["prompt_id"] == "haiku_prompt"