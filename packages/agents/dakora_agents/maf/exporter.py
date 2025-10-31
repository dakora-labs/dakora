"""OpenTelemetry SpanExporter for Dakora API integration."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Sequence

import httpx
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

if TYPE_CHECKING:
    from dakora_client import Dakora

__all__ = ["DakoraSpanExporter"]

logger = logging.getLogger(__name__)


class DakoraSpanExporter(SpanExporter):
    """
    OTEL SpanExporter that sends agent execution spans to Dakora API.

    This exporter:
    - Filters for agent invocation and chat spans
    - Converts to standard OTLP format
    - Batches spans together (standard OTLP behavior)
    - Sends to /api/v1/traces endpoint

    The server handles all extraction and processing logic, including:
    - Smart recompute for late-arriving spans
    - Template linkage extraction
    - Conversation history parsing
    - Model/provider normalization

    Used with MAF's DakoraIntegration.setup() for automatic export.
    """

    def __init__(self, dakora_client: Dakora):
        """
        Initialize the exporter.

        Args:
            dakora_client: Dakora client instance with API key configured
        """
        # Extract connection details from async client
        self._base_url = dakora_client.base_url
        self._api_key = getattr(dakora_client, "_Dakora__api_key", None)
        self._project_id = dakora_client.project_id  # Already fetched during client initialization

        # Create a synchronous HTTP client for exports
        # OTEL exporters must be synchronous, so we can't use the async Dakora client
        self._http_client = httpx.Client(
            base_url=self._base_url,
            headers={"X-API-Key": self._api_key} if self._api_key else {},
            timeout=30.0,
        )

        logger.info(
            f"DakoraSpanExporter initialized (base_url={self._base_url}, project_id={self._project_id})"
        )

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export spans to Dakora API (synchronous).

        Called automatically by OTEL BatchSpanProcessor in its background thread.
        This method MUST be synchronous - OTEL handles threading for us.

        Batching Strategy:
        - Sends ALL spans in the batch together (standard OTLP behavior)
        - Server handles extraction with smart recompute logic

        Args:
            spans: Sequence of completed OTEL spans

        Returns:
            SpanExportResult.SUCCESS or SpanExportResult.FAILURE
        """
        try:
            logger.debug(f"DakoraSpanExporter.export called with {len(spans)} spans")

            # Skip if no project_id (exporter initialized without API key)
            if not self._project_id:
                logger.debug("Skipping export: no project_id available")
                return SpanExportResult.SUCCESS

            # Filter for agent spans only (keep invoke_agent and chat spans)
            agent_spans = [span for span in spans if self._is_agent_span(span)]

            if not agent_spans:
                logger.debug(f"No agent spans to export (filtered {len(spans)} spans)")
                return SpanExportResult.SUCCESS

            logger.info(f"Exporting {len(agent_spans)} agent span(s) to Dakora")

            # Convert all spans to OTLP format
            otlp_spans = []
            for span in agent_spans:
                attrs = span.attributes or {}
                trace_id = self._format_trace_id(span.context.trace_id)
                span_id = self._format_span_id(span.context.span_id)
                parent_span_id = self._format_span_id(span.parent.span_id) if span.parent else None

                otlp_span = {
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "span_name": span.name,
                    "span_kind": attrs.get("gen_ai.operation.name"),
                    "attributes": dict(attrs),
                    "events": [{"name": e.name, "attributes": dict(e.attributes or {})} for e in span.events],
                    "start_time_ns": span.start_time,
                    "end_time_ns": span.end_time,
                    "status_code": None,  # Could extract from span.status
                    "status_message": None,
                }
                otlp_spans.append(otlp_span)

            # Build batch payload (all spans together)
            payload = {"spans": otlp_spans}

            # PRINT PAYLOAD BEING SENT TO DAKORA
            print("\n" + "="*80)
            print(f"OTLP BATCH PAYLOAD ({len(otlp_spans)} spans):")
            print("="*80)
            print(json.dumps(payload, indent=2, default=str))
            print("="*80 + "\n")

            # Make synchronous HTTP POST to OTLP endpoint
            url = "/api/v1/traces"
            logger.debug(f"POST {url} with {len(otlp_spans)} spans")

            response = self._http_client.post(url, json=payload)
            response.raise_for_status()

            logger.info(f"Successfully exported {len(agent_spans)} span(s) (status={response.status_code})")
            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to export spans to Dakora: {e}", exc_info=True)
            return SpanExportResult.FAILURE


    def _is_agent_span(self, span: ReadableSpan) -> bool:
        """
        Check if this is an agent invocation span we should export.

        Supports multiple operation name formats for compatibility with different MAF versions.

        Args:
            span: OTEL span to check

        Returns:
            True if this is an agent invocation span
        """
        attrs = span.attributes or {}
        operation = attrs.get("gen_ai.operation.name")
        # Support current and potential future MAF operation names
        return operation in ("invoke_agent", "agent.invoke", "chat.invoke", "agent_invoke", "chat")

    def _format_trace_id(self, trace_id: int) -> str:
        """
        Format OTEL trace_id (int) to hex string.

        Args:
            trace_id: OTEL trace ID (128-bit integer)

        Returns:
            Hex string (32 characters)
        """
        return f"{trace_id:032x}"

    def _format_span_id(self, span_id: int) -> str:
        """
        Format OTEL span_id (int) to hex string.

        Args:
            span_id: OTEL span ID (64-bit integer)

        Returns:
            Hex string (16 characters)
        """
        return f"{span_id:016x}"

    def shutdown(self) -> None:
        """Called when SDK shuts down."""
        try:
            self._http_client.close()
            logger.debug("DakoraSpanExporter shutdown complete")
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Ensure all spans are exported before returning.

        Args:
            timeout_millis: Timeout in milliseconds

        Returns:
            True if flush succeeded
        """
        # BatchSpanProcessor handles flushing, we just return success
        return True