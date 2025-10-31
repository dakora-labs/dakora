"""Unit tests for OTLP processor logic without database.

Tests the orchestration logic for span processing.
"""

from uuid import uuid4

import pytest
from unittest.mock import Mock, MagicMock

from dakora_server.api.otlp_traces import OTLPSpan
from dakora_server.core.otlp_processor import (
    _get_unique_trace_ids,
)


def create_test_span(trace_id: str, span_id: str, parent_id: str | None = None) -> OTLPSpan:
    """Helper to create test spans."""
    return OTLPSpan(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_id,
        span_name=f"span-{span_id}",
        span_kind="chat",
        attributes={"gen_ai.operation.name": "chat"},
        events=[],
        start_time_ns=1000000000,
        end_time_ns=2000000000,
        status_code=None,
        status_message=None,
    )


# Tests for _get_unique_trace_ids


def test_get_unique_trace_ids_single_trace():
    """Should extract single unique trace ID."""
    spans = [
        create_test_span("trace-1", "span-1"),
        create_test_span("trace-1", "span-2"),
    ]

    trace_ids = _get_unique_trace_ids(spans)

    assert len(trace_ids) == 1
    assert "trace-1" in trace_ids


def test_get_unique_trace_ids_multiple_traces():
    """Should extract multiple unique trace IDs."""
    spans = [
        create_test_span("trace-1", "span-1"),
        create_test_span("trace-2", "span-2"),
        create_test_span("trace-1", "span-3"),
        create_test_span("trace-3", "span-4"),
    ]

    trace_ids = _get_unique_trace_ids(spans)

    assert len(trace_ids) == 3
    assert set(trace_ids) == {"trace-1", "trace-2", "trace-3"}


def test_get_unique_trace_ids_empty():
    """Should handle empty span list."""
    trace_ids = _get_unique_trace_ids([])
    assert len(trace_ids) == 0


# Test edge cases for span hierarchy


def test_orphaned_child_span():
    """Should handle child span when parent is missing from batch."""
    from dakora_server.core.otlp_extractor import build_span_hierarchy

    # Child references parent that doesn't exist in batch
    child = create_test_span("trace-1", "child-1", parent_id="missing-parent")

    hierarchy = build_span_hierarchy([child])

    # Should have entry for missing parent
    assert "missing-parent" in hierarchy
    assert len(hierarchy["missing-parent"]) == 1


def test_circular_parent_reference():
    """Should handle potential circular references gracefully."""
    from dakora_server.core.otlp_extractor import build_span_hierarchy

    # This is an invalid scenario, but code should not crash
    span1 = create_test_span("trace-1", "span-1", parent_id="span-2")
    span2 = create_test_span("trace-1", "span-2", parent_id="span-1")

    # Should build hierarchy without crashing
    hierarchy = build_span_hierarchy([span1, span2])

    assert "span-1" in hierarchy
    assert "span-2" in hierarchy


# Test data aggregation priority


def test_model_aggregation_priority():
    """Should prefer dakora.model over gen_ai.* attributes."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    root_attrs = {
        "gen_ai.request.model": "fallback-model",
        "dakora.model": "priority-model",
    }
    root = create_test_span("trace-1", "root")
    root.attributes = root_attrs
    root.parent_span_id = None

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["model"] == "priority-model"


def test_tokens_fallback_to_root():
    """Should fallback to root span if child has no tokens."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    root_attrs = {
        "gen_ai.usage.input_tokens": 100,
        "gen_ai.usage.output_tokens": 50,
    }
    root = create_test_span("trace-1", "root")
    root.attributes = root_attrs
    root.parent_span_id = None

    # Child with no token info
    child = create_test_span("trace-1", "child", parent_id="root")
    child.attributes = {}

    hierarchy = build_span_hierarchy([root, child])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    # Should use root's tokens
    assert trace_data["tokens_in"] == 100
    assert trace_data["tokens_out"] == 50


def test_conversation_empty_when_both_missing():
    """Should return empty conversation when no messages in root or children."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    root = create_test_span("trace-1", "root")
    root.attributes = {}
    root.parent_span_id = None

    child = create_test_span("trace-1", "child", parent_id="root")
    child.attributes = {}

    hierarchy = build_span_hierarchy([root, child])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["conversation_history"] == []


# Test metadata extraction


def test_metadata_excludes_reserved_keys():
    """Should exclude reserved dakora.* keys from metadata."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    attrs = {
        "dakora.custom_field": "should_be_included",
        "dakora.model": "should_be_excluded",
        "dakora.template_contexts": "should_be_excluded",
        "dakora.session_id": "should_be_excluded",
        "dakora.source": "should_be_excluded",
        "dakora.another_custom": "should_be_included",
    }
    root = create_test_span("trace-1", "root")
    root.attributes = attrs
    root.parent_span_id = None

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    metadata = trace_data["metadata"]
    assert metadata is not None
    assert "custom_field" in metadata
    assert "another_custom" in metadata
    assert "model" not in metadata
    assert "template_contexts" not in metadata
    assert "session_id" not in metadata
    assert "source" not in metadata


def test_metadata_none_when_no_custom_fields():
    """Should set metadata to None when no custom dakora.* fields."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    attrs = {
        "dakora.model": "test",  # Reserved
        "gen_ai.operation.name": "chat",  # Not dakora.*
    }
    root = create_test_span("trace-1", "root")
    root.attributes = attrs
    root.parent_span_id = None

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    assert trace_data["metadata"] is None


# Test latency calculation


def test_latency_calculation():
    """Should correctly calculate latency in milliseconds."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    root = create_test_span("trace-1", "root")
    root.start_time_ns = 1000000000  # 1s
    root.end_time_ns = 3500000000     # 3.5s
    root.parent_span_id = None

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    # 2.5s = 2500ms
    assert trace_data["latency_ms"] == 2500


def test_latency_sub_millisecond():
    """Should handle sub-millisecond latencies."""
    from dakora_server.core.otlp_extractor import extract_execution_trace, build_span_hierarchy

    root = create_test_span("trace-1", "root")
    root.start_time_ns = 1000000000
    root.end_time_ns = 1000500000  # 500 microseconds = 0.5ms
    root.parent_span_id = None

    hierarchy = build_span_hierarchy([root])
    project_id = uuid4()

    trace_data = extract_execution_trace(root, hierarchy, project_id)

    # Should round down to 0
    assert trace_data["latency_ms"] == 0


# Test MAF parts format edge cases


def test_conversation_mixed_content_and_parts():
    """Should handle messages with both content and parts (prefer content)."""
    import json
    from dakora_server.core.otlp_extractor import extract_conversation_history

    attrs = {
        "gen_ai.input.messages": json.dumps([
            {
                "role": "user",
                "content": "Direct content",
                "parts": [{"type": "text", "content": "Parts content"}]
            }
        ]),
    }
    span = create_test_span("trace-1", "span-1")
    span.attributes = attrs

    history = extract_conversation_history(span)

    # Should use direct content field
    assert history[0]["content"] == "Direct content"


def test_conversation_parts_with_non_text_types():
    """Should ignore non-text parts."""
    import json
    from dakora_server.core.otlp_extractor import extract_conversation_history

    attrs = {
        "gen_ai.input.messages": json.dumps([
            {
                "role": "user",
                "parts": [
                    {"type": "text", "content": "Text part"},
                    {"type": "image", "url": "http://example.com/img.jpg"},
                    {"type": "text", "content": "Another text"}
                ]
            }
        ]),
    }
    span = create_test_span("trace-1", "span-1")
    span.attributes = attrs

    history = extract_conversation_history(span)

    # Should only extract text parts
    assert history[0]["content"] == "Text part\nAnother text"


# Performance tests (validation only, no timing)


def test_hierarchy_handles_large_batches():
    """Should handle large span batches efficiently."""
    from dakora_server.core.otlp_extractor import build_span_hierarchy

    # Create 1000 spans with 100 traces
    spans = []
    for trace_num in range(100):
        trace_id = f"trace-{trace_num}"
        # 1 root + 9 children per trace
        spans.append(create_test_span(trace_id, f"root-{trace_num}", None))
        for child_num in range(9):
            spans.append(
                create_test_span(trace_id, f"child-{trace_num}-{child_num}", f"root-{trace_num}")
            )

    # Should complete without error
    hierarchy = build_span_hierarchy(spans)

    # Verify correctness
    assert len(hierarchy) == 100  # 100 roots with children
    for trace_num in range(100):
        root_id = f"root-{trace_num}"
        assert len(hierarchy[root_id]) == 9  # 9 children each


def test_unique_trace_ids_deduplicates():
    """Should deduplicate trace IDs efficiently."""
    # 1000 spans across 10 traces (100 spans per trace)
    spans = []
    for trace_num in range(10):
        trace_id = f"trace-{trace_num}"
        for span_num in range(100):
            spans.append(create_test_span(trace_id, f"span-{trace_num}-{span_num}"))

    trace_ids = _get_unique_trace_ids(spans)

    assert len(trace_ids) == 10
    assert all(f"trace-{i}" in trace_ids for i in range(10))