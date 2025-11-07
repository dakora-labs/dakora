"""Parse OTLP protobuf format into OTLPSpan objects."""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from opentelemetry.proto.trace.v1.trace_pb2 import (
    TracesData,
    Span as ProtoSpan,
)

if TYPE_CHECKING:
    from dakora_server.api.otlp_traces import OTLPSpan

logger = logging.getLogger(__name__)


def parse_otlp_protobuf(data: bytes) -> list[OTLPSpan]:
    """
    Parse OTLP protobuf binary data into OTLPSpan objects.

    Args:
        data: Raw protobuf bytes from OTLP HTTP exporter

    Returns:
        List of OTLPSpan objects

    Raises:
        ValueError: If protobuf parsing fails
    """
    from dakora_server.api.otlp_traces import OTLPSpan

    try:
        # Parse protobuf
        traces_data = TracesData()
        traces_data.ParseFromString(data)

        spans: list[OTLPSpan] = []

        # Iterate through resource spans
        for resource_span in traces_data.resource_spans:
            # Iterate through scope spans
            for scope_span in resource_span.scope_spans:
                # Iterate through spans
                for proto_span in scope_span.spans:
                    span = _convert_proto_span(proto_span)
                    spans.append(span)

        logger.debug(f"Parsed {len(spans)} span(s) from protobuf")
        return spans

    except Exception as e:
        logger.error(f"Failed to parse OTLP protobuf: {e}", exc_info=True)
        raise ValueError(f"Invalid OTLP protobuf data: {e}") from e


def _convert_proto_span(proto_span: ProtoSpan) -> OTLPSpan:
    """
    Convert a protobuf Span to OTLPSpan.

    Args:
        proto_span: Protobuf span object

    Returns:
        OTLPSpan object
    """
    from dakora_server.api.otlp_traces import OTLPSpan

    # Convert trace_id and span_id from bytes to hex string
    trace_id = proto_span.trace_id.hex()
    span_id = proto_span.span_id.hex()
    parent_span_id = proto_span.parent_span_id.hex() if proto_span.parent_span_id else None

    # Extract attributes
    attributes: dict[str, Any] = {}
    for kv in proto_span.attributes:
        key = kv.key
        value = _extract_attribute_value(kv.value)
        attributes[key] = value

    # Extract events
    events: list[dict[str, Any]] = []
    for event in proto_span.events:
        event_dict: dict[str, Any] = {
            "name": event.name,
            "time_unix_nano": event.time_unix_nano,
            "attributes": {},
        }
        for kv in event.attributes:
            event_dict["attributes"][kv.key] = _extract_attribute_value(kv.value)
        events.append(event_dict)

    # Map span kind
    span_kind_map = {
        0: "UNSPECIFIED",
        1: "INTERNAL",
        2: "SERVER",
        3: "CLIENT",
        4: "PRODUCER",
        5: "CONSUMER",
    }
    span_kind = span_kind_map.get(proto_span.kind, "UNSPECIFIED")

    # Map status code
    status_code_map = {
        0: "UNSET",
        1: "OK",
        2: "ERROR",
    }
    status_code = status_code_map.get(proto_span.status.code, "UNSET")
    status_message = proto_span.status.message if proto_span.status.message else None

    return OTLPSpan(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        span_name=proto_span.name,
        span_kind=span_kind,
        attributes=attributes,
        events=events,
        start_time_ns=proto_span.start_time_unix_nano,
        end_time_ns=proto_span.end_time_unix_nano,
        status_code=status_code,
        status_message=status_message,
    )


def _extract_attribute_value(value: Any) -> Any:
    """
    Extract value from OTLP AnyValue protobuf.

    Args:
        value: OTLP AnyValue object

    Returns:
        Python value (str, int, float, bool, list, dict)
    """
    # Check which field is set
    which = value.WhichOneof("value")

    if which == "string_value":
        return value.string_value
    elif which == "bool_value":
        return value.bool_value
    elif which == "int_value":
        return value.int_value
    elif which == "double_value":
        return value.double_value
    elif which == "array_value":
        return [_extract_attribute_value(v) for v in value.array_value.values]
    elif which == "kvlist_value":
        result = {}
        for kv in value.kvlist_value.values:
            result[kv.key] = _extract_attribute_value(kv.value)
        return result
    elif which == "bytes_value":
        return value.bytes_value.hex()
    else:
        return None