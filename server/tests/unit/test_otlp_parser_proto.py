"""Tests for OTLP protobuf parser.

Skips if opentelemetry proto classes are not available. Validates that
parse_otlp_protobuf converts a minimal TracesData payload into OTLPSpan
objects and that invalid bytes raise ValueError.
"""

from __future__ import annotations

import binascii
import pytest


proto = pytest.importorskip("opentelemetry.proto.trace.v1.trace_pb2")


def _bytes_from_hex(hex_str: str) -> bytes:
    return binascii.unhexlify(hex_str.encode())


def test_parse_minimal_tracesdata_roundtrip():
    from dakora_server.core.otlp_parser import parse_otlp_protobuf

    traces = proto.TracesData()
    rspan = traces.resource_spans.add()
    sspan = rspan.scope_spans.add()
    span = sspan.spans.add()

    span.trace_id = _bytes_from_hex("0123456789abcdef0123456789abcdef")  # 16 bytes
    span.span_id = _bytes_from_hex("0123456789abcdef")  # 8 bytes
    span.parent_span_id = b""  # None
    span.name = "chat"
    span.kind = 1  # INTERNAL
    span.start_time_unix_nano = 1_000_000_000
    span.end_time_unix_nano = 2_000_000_000
    span.status.code = 1  # OK
    span.status.message = ""

    # Attribute: operation name
    kv = span.attributes.add()
    kv.key = "gen_ai.operation.name"
    kv.value.string_value = "chat"

    # Attribute: nested kvlist
    nested = span.attributes.add()
    nested.key = "nested"
    kvlist = nested.value.kvlist_value
    i1 = kvlist.values.add()
    i1.key = "a"
    i1.value.int_value = 42
    i2 = kvlist.values.add()
    i2.key = "flag"
    i2.value.bool_value = True

    # Attribute: array
    arr = span.attributes.add()
    arr.key = "arr"
    av = arr.value.array_value
    av.values.add().string_value = "x"
    av.values.add().string_value = "y"

    # Parse
    out = parse_otlp_protobuf(traces.SerializeToString())
    assert len(out) == 1
    s = out[0]

    # ID fields converted to hex strings
    assert s.trace_id == "0123456789abcdef0123456789abcdef"
    assert s.span_id == "0123456789abcdef"
    assert s.parent_span_id is None

    # Mapping fields
    assert s.span_name == "chat"
    assert s.span_kind == "INTERNAL"
    assert s.start_time_ns == 1_000_000_000
    assert s.end_time_ns == 2_000_000_000
    assert s.status_code == "OK"
    assert s.status_message is None

    # Attribute extraction
    assert s.attributes["gen_ai.operation.name"] == "chat"
    assert s.attributes["nested"]["a"] == 42
    assert s.attributes["nested"]["flag"] is True
    assert s.attributes["arr"] == ["x", "y"]


def test_parse_invalid_bytes_raises_value_error():
    from dakora_server.core.otlp_parser import parse_otlp_protobuf

    with pytest.raises(ValueError):
        parse_otlp_protobuf(b"\x00\x01invalid")

