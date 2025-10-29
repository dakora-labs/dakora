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
    - Filters for agent invocation spans only
    - Extracts template linkage from message events
    - Transforms OTEL spans → Dakora API format
    - Sends to /api/projects/{project_id}/executions endpoint

    Used with MAF's setup_observability() for automatic export.
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

        Args:
            spans: Sequence of completed OTEL spans

        Returns:
            SpanExportResult.SUCCESS or SpanExportResult.FAILURE
        """
        try:
            logger.debug(f"DakoraSpanExporter.export called with {len(spans)} spans")

            # Filter for agent spans only
            agent_spans = [span for span in spans if self._is_agent_span(span)]

            if not agent_spans:
                logger.debug(f"No agent spans to export (filtered {len(spans)} spans)")
                return SpanExportResult.SUCCESS

            logger.info(f"Exporting {len(agent_spans)} agent span(s) to Dakora")

            # Build a span lookup map for correlation (span_id -> span)
            span_map = {self._format_span_id(span.context.span_id): span for span in spans}

            # Export each span synchronously
            success_count = 0
            for span in agent_spans:
                if self._export_span_sync(span, span_map):
                    success_count += 1

            logger.info(f"Successfully exported {success_count}/{len(agent_spans)} spans")
            return SpanExportResult.SUCCESS if success_count > 0 else SpanExportResult.FAILURE

        except Exception as e:
            logger.error(f"Failed to export spans to Dakora: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def _export_span_sync(self, span: ReadableSpan, span_map: dict[str, ReadableSpan]) -> bool:
        """
        Export a single span synchronously using synchronous HTTP client.

        Args:
            span: Agent invocation span from OTEL
            span_map: Map of span_id -> span for correlation

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            # Skip if no project_id (exporter initialized without API key)
            if not self._project_id:
                logger.debug("Skipping span export: no project_id available")
                return False

            # Build payload (pass span_map for parent correlation)
            payload = self._build_payload(span, span_map)

            # DEBUG: Log the full payload to verify template linkage
            logger.debug(f"Full payload being sent to Dakora:\n{json.dumps(payload, indent=2)}")

            # Make synchronous HTTP POST
            url = f"/api/projects/{self._project_id}/executions"
            logger.debug(f"POST {url}")

            response = self._http_client.post(url, json=payload)
            response.raise_for_status()

            trace_id = payload.get("trace_id", "unknown")
            logger.debug(f"Exported trace {trace_id} to Dakora (status={response.status_code})")
            return True

        except Exception as e:
            trace_id = self._format_trace_id(span.context.trace_id) if span.context else "unknown"
            logger.warning(f"Failed to export trace {trace_id}: {e}")
            return False

    def _normalize_provider(self, raw_provider: str) -> str | None:
        """
        Normalize provider name from MAF to Dakora format.

        MAF formats:
        - "azure.ai.openai" → "azure_openai"
        - "microsoft.agent_framework" → "azure_openai" (default for MAF)
        - "openai" → "openai"

        Args:
            raw_provider: Raw provider string from MAF

        Returns:
            Normalized provider name for Dakora pricing table
        """
        if not raw_provider:
            return None

        raw_lower = raw_provider.lower()

        # Map MAF provider strings to Dakora pricing table format
        if "azure" in raw_lower or "microsoft" in raw_lower:
            return "azure_openai"
        elif "openai" in raw_lower:
            return "openai"
        elif "anthropic" in raw_lower or "claude" in raw_lower:
            return "anthropic"
        elif "google" in raw_lower or "gemini" in raw_lower:
            return "google"

        # Return as-is if we don't recognize it
        logger.debug(f"Unknown provider format: {raw_provider}, returning as-is")
        return raw_provider

    def _normalize_model(self, raw_model: str) -> str | None:
        """
        Normalize model name from MAF to Dakora format.

        MAF formats:
        - "gpt-4o-mini-2024-07-18" → "gpt-4o-mini"
        - "gpt-35-turbo-16k" → "gpt-35-turbo-16k"

        Strips date suffixes and version tags while preserving core model name.

        Args:
            raw_model: Raw model string from MAF

        Returns:
            Normalized model name for Dakora pricing table
        """
        if not raw_model:
            return None

        # Strip date suffixes (e.g., "-2024-07-18")
        # Pattern: model name followed by -YYYY-MM-DD
        import re
        normalized = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', raw_model)

        logger.debug(f"Normalized model: {raw_model} → {normalized}")
        return normalized

    def _build_payload(self, span: ReadableSpan, span_map: dict[str, ReadableSpan]) -> dict[str, Any]:
        """
        Build Dakora API payload from OTEL span.

        Gracefully handles MAF format changes - if extraction fails, sends without that field.

        Args:
            span: Agent invocation span
            span_map: Map of span_id -> span for parent correlation
        """
        attrs = span.attributes or {}

        # Debug: Log ALL attributes to understand what MAF provides
        logger.debug(f"All span attributes: {dict(attrs)}")

        # NOTE: We no longer need parent span correlation!
        # The middleware now sets dakora.* attributes AFTER next(), so they're
        # directly on the agent invocation span that we export here.

        # Extract OTEL standard attributes (defensive - use .get() with defaults)
        agent_id = attrs.get("gen_ai.agent.id")

        # Provider: Parse from gen_ai.provider.name
        # MAF sets this to values like "azure.ai.openai" or "microsoft.agent_framework"
        raw_provider = attrs.get("gen_ai.provider.name", "")
        provider = self._normalize_provider(raw_provider)
        logger.debug(f"Provider: {raw_provider} → {provider}")

        # Model: Prefer dakora.model (set by middleware from client.model_id)
        # Fallback to gen_ai.response.model or gen_ai.request.model
        raw_model = (
            attrs.get("dakora.model")
            or attrs.get("gen_ai.response.model")
            or attrs.get("gen_ai.request.model")
        )
        model = self._normalize_model(raw_model) if raw_model else None
        logger.debug(f"Model: {raw_model} → {model}")

        tokens_in = attrs.get("gen_ai.usage.input_tokens")
        tokens_out = attrs.get("gen_ai.usage.output_tokens")

        # Calculate latency in milliseconds (defensive - fallback to 0)
        try:
            latency_ms = int((span.end_time - span.start_time) / 1_000_000)  # ns → ms
        except (TypeError, ValueError, AttributeError):
            logger.debug("Failed to calculate latency, using 0")
            latency_ms = 0

        # Format trace and parent IDs (defensive)
        try:
            trace_id = self._format_trace_id(span.context.trace_id)
        except (TypeError, ValueError, AttributeError):
            logger.debug("Failed to format trace_id, using fallback")
            trace_id = "unknown"

        parent_trace_id = None
        if span.parent:
            try:
                parent_trace_id = self._format_span_id(span.parent.span_id)
            except (TypeError, ValueError, AttributeError):
                logger.debug("Failed to format parent_trace_id")

        # Extract conversation history and template linkage (defensive)
        # If MAF changes format, we send without these fields rather than failing
        try:
            conversation_history = self._extract_conversation_history(span)
        except Exception as e:
            logger.debug(f"Failed to extract conversation history: {e}")
            conversation_history = []

        try:
            template_usages = self._extract_template_usages(span)
        except Exception as e:
            logger.debug(f"Failed to extract template usages: {e}")
            template_usages = None

        try:
            metadata = self._extract_metadata(attrs)
        except Exception as e:
            logger.debug(f"Failed to extract metadata: {e}")
            metadata = None

        # Generate session_id if not provided
        session_id = attrs.get("dakora.session_id") or trace_id

        # Build payload using project_id from exporter initialization
        payload = {
            "project_id": self._project_id,
            "trace_id": trace_id,
            "parent_trace_id": parent_trace_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "source": attrs.get("dakora.source", "maf"),
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "conversation_history": conversation_history,
            "template_usages": template_usages,
            "metadata": metadata,
        }

        # Remove None values
        return {k: v for k, v in payload.items() if v is not None}

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
        return operation in ("invoke_agent", "agent.invoke", "chat.invoke", "agent_invoke")

    def _extract_conversation_history(self, span: ReadableSpan) -> list[dict[str, Any]]:
        """
        Extract conversation history from OTEL span events.

        MAF captures messages as span events with names like:
        - gen_ai.user.message
        - gen_ai.assistant.message
        - gen_ai.system.message
        - gen_ai.tool.message

        Args:
            span: OTEL span with message events

        Returns:
            List of conversation messages
        """
        history = []
        attrs = span.attributes or {}

        # Try to parse from gen_ai.input.messages and gen_ai.output.messages attributes
        input_messages_json = attrs.get("gen_ai.input.messages")
        output_messages_json = attrs.get("gen_ai.output.messages")

        if input_messages_json:
            try:
                input_messages = json.loads(input_messages_json)
                for idx, msg in enumerate(input_messages):
                    history.append(
                        {
                            "index": idx,
                            "role": msg.get("role", "user"),
                            "content": self._extract_message_content(msg),
                            "dakora_template": msg.get("dakora_template"),
                        }
                    )
            except (json.JSONDecodeError, TypeError):
                logger.debug("Failed to parse gen_ai.input.messages")

        if output_messages_json:
            try:
                output_messages = json.loads(output_messages_json)
                start_idx = len(history)
                for idx, msg in enumerate(output_messages):
                    history.append(
                        {
                            "index": start_idx + idx,
                            "role": msg.get("role", "assistant"),
                            "content": self._extract_message_content(msg),
                            "dakora_template": msg.get("dakora_template"),
                        }
                    )
            except (json.JSONDecodeError, TypeError):
                logger.debug("Failed to parse gen_ai.output.messages")

        # Fallback: Extract from span events if attributes don't have messages
        if not history:
            message_events = [
                "gen_ai.user.message",
                "gen_ai.assistant.message",
                "gen_ai.system.message",
                "gen_ai.tool.message",
                "gen_ai.choice",
            ]

            for idx, event in enumerate(span.events):
                if event.name in message_events:
                    event_attrs = event.attributes or {}
                    history.append(
                        {
                            "index": idx,
                            "role": event_attrs.get("role", "user"),
                            "content": event_attrs.get("content", ""),
                            "dakora_template": event_attrs.get("dakora_template"),
                        }
                    )

        return history

    def _extract_message_content(self, msg: dict[str, Any]) -> str:
        """
        Extract text content from a message dict.

        Handles both simple text and complex part-based messages.

        Args:
            msg: Message dictionary

        Returns:
            Text content
        """
        # Try 'content' field first
        if isinstance(msg.get("content"), str):
            return msg["content"]

        # Try 'parts' array (MAF format)
        parts = msg.get("parts", [])
        if parts:
            text_parts = []
            for part in parts:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("content", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            return "\n".join(text_parts)

        # Fallback
        return str(msg.get("text", ""))

    def _extract_template_usages(self, span: ReadableSpan) -> list[dict[str, Any]] | None:
        """
        Extract template linkage from span attributes or conversation history.

        Templates are identified by:
        1. dakora.template_contexts attribute (set by middleware) - PREFERRED
        2. _dakora_context attribute on messages in conversation history - FALLBACK

        Args:
            span: OTEL span with template contexts

        Returns:
            List of template usages or None
        """
        template_usages = []
        attrs = span.attributes or {}

        # PREFERRED: Extract from dakora.template_contexts (set by middleware)
        template_contexts_json = attrs.get("dakora.template_contexts")
        if template_contexts_json:
            try:
                template_contexts = json.loads(template_contexts_json)
                for idx, ctx in enumerate(template_contexts):
                    if isinstance(ctx, dict):
                        template_usages.append(
                            {
                                "prompt_id": ctx.get("prompt_id"),
                                "version": ctx.get("version"),
                                "inputs": ctx.get("inputs", {}),
                                "metadata": ctx.get("metadata", {}),
                                "role": ctx.get("role", "user"),
                                "source": "message",
                                "message_index": idx,
                            }
                        )
                logger.debug(f"Extracted {len(template_usages)} template(s) from dakora.template_contexts")
                return template_usages if template_usages else None
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse dakora.template_contexts: {e}")

        # FALLBACK: Extract from conversation history (old method)
        history = self._extract_conversation_history(span)

        for msg in history:
            dakora_ctx = msg.get("dakora_template")
            if dakora_ctx and isinstance(dakora_ctx, dict):
                template_usages.append(
                    {
                        "prompt_id": dakora_ctx.get("prompt_id"),
                        "version": dakora_ctx.get("version"),
                        "inputs": dakora_ctx.get("inputs", {}),
                        "metadata": dakora_ctx.get("metadata", {}),
                        "role": msg.get("role"),
                        "source": "message",
                        "message_index": msg.get("index"),
                    }
                )

        if template_usages:
            logger.debug(f"Extracted {len(template_usages)} template(s) from conversation history")

        return template_usages if template_usages else None

    def _extract_metadata(self, attrs: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract Dakora-specific metadata from span attributes.

        Collects all attributes with 'dakora.' prefix (except reserved keys used for other fields).

        Args:
            attrs: Span attributes

        Returns:
            Metadata dictionary or None
        """
        metadata = {}

        # Reserved keys that go to top-level fields or are handled separately
        reserved = {
            "dakora.project_id",
            "dakora.session_id",
            "dakora.source",
            "dakora.provider",  # Used for provider field
            "dakora.model",  # Used for model field
            "dakora.template_contexts",  # Used for template_usages field
        }

        for key, value in attrs.items():
            if key.startswith("dakora.") and key not in reserved:
                # Strip "dakora." prefix
                metadata[key[7:]] = value

        return metadata if metadata else None

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