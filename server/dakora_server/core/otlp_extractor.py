"""Extract execution traces from OTLP spans for UI consumption."""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import Any, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from dakora_server.api.otlp_traces import OTLPSpan

logger = logging.getLogger(__name__)


def build_span_hierarchy(spans: list[OTLPSpan]) -> dict[str, list[OTLPSpan]]:
    """
    Build a lookup dict for efficient child span queries.

    Returns dict mapping parent_span_id -> list of child spans.
    This avoids O(n²) lookups when processing multiple spans.

    Args:
        spans: All spans in the batch

    Returns:
        Dict mapping parent span_id to list of child spans
    """
    children_by_parent: dict[str, list[OTLPSpan]] = defaultdict(list)
    for span in spans:
        if span.parent_span_id:
            children_by_parent[span.parent_span_id].append(span)
    return dict(children_by_parent)


def is_root_execution_span(span: OTLPSpan) -> bool:
    """
    Determine if this span should create an execution trace.

    Standard OTLP approach:
    - Root span = parent_span_id is None (standard Jaeger/Zipkin behavior)
    - Must be an agent/chat operation

    Args:
        span: OTLP span to check

    Returns:
        True if this span should create an execution trace
    """
    # Must have no parent (standard OTLP root detection)
    if span.parent_span_id:
        return False

    # Must be an agent operation
    attrs = span.attributes or {}
    operation = attrs.get("gen_ai.operation.name")
    return operation in ("invoke_agent", "chat", "agent.invoke", "chat.invoke", "agent_invoke")


def normalize_provider(raw_provider: str | None) -> str | None:
    """Normalize provider name from OTLP to Dakora format."""
    if not raw_provider:
        return None

    raw_lower = raw_provider.lower()

    if "azure" in raw_lower or "microsoft" in raw_lower:
        return "azure_openai"
    elif "openai" in raw_lower:
        return "openai"
    elif "anthropic" in raw_lower or "claude" in raw_lower:
        return "anthropic"
    elif "google" in raw_lower or "gemini" in raw_lower:
        return "google"

    return raw_provider


def normalize_model(raw_model: str | None) -> str | None:
    """Normalize model name from OTLP to Dakora format."""
    if not raw_model or raw_model.lower() == "unknown":
        return None

    # Strip date suffixes (e.g., "-2024-07-18")
    normalized = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', raw_model)
    return normalized


def extract_conversation_history(span: OTLPSpan) -> list[dict[str, Any]]:
    """Extract conversation messages from OTLP span."""
    attrs = span.attributes or {}
    history = []

    # Parse input messages
    input_messages_json = attrs.get("gen_ai.input.messages")
    if input_messages_json:
        try:
            input_messages = json.loads(input_messages_json)
            for idx, msg in enumerate(input_messages):
                content = msg.get("content", "")

                # Handle part-based messages (MAF format)
                if not content and msg.get("parts"):
                    parts = msg["parts"]
                    text_parts = []
                    for part in parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("content", ""))
                    content = "\n".join(text_parts)

                history.append({
                    "role": msg.get("role", "user"),
                    "content": content,
                })
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse input messages: {e}")

    # Parse output messages
    output_messages_json = attrs.get("gen_ai.output.messages")
    if output_messages_json:
        try:
            output_messages = json.loads(output_messages_json)
            for msg in output_messages:
                content = msg.get("content", "")

                # Handle part-based messages
                if not content and msg.get("parts"):
                    parts = msg["parts"]
                    text_parts = []
                    for part in parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_parts.append(part.get("content", ""))
                    content = "\n".join(text_parts)

                history.append({
                    "role": msg.get("role", "assistant"),
                    "content": content,
                })
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse output messages: {e}")

    return history


def extract_template_usages(
    root_span: OTLPSpan,
    span_hierarchy: dict[str, list[OTLPSpan]]
) -> list[dict[str, Any]] | None:
    """
    Extract template linkage from OTLP span.

    Checks root span and child spans for template contexts.

    Args:
        root_span: Root span to extract from
        span_hierarchy: Dict mapping parent_span_id -> children (from build_span_hierarchy)

    Returns:
        List of template usages or None
    """
    # Get child spans from hierarchy (O(1) lookup)
    child_spans = span_hierarchy.get(root_span.span_id, [])

    # Try root first, then children
    for span in [root_span] + child_spans:
        attrs = span.attributes or {}
        template_contexts_json = attrs.get("dakora.template_contexts")

        if not template_contexts_json:
            continue

        try:
            template_contexts = json.loads(template_contexts_json)
            usages = []

            for idx, ctx in enumerate(template_contexts):
                if isinstance(ctx, dict):
                    usages.append({
                        "prompt_id": ctx.get("prompt_id"),
                        "version": ctx.get("version"),
                        "inputs_json": ctx.get("inputs", {}),
                        "position": idx,
                        "role": ctx.get("role", "user"),
                        "source": "message",
                        "message_index": idx,
                        "metadata_json": ctx.get("metadata", {}),
                    })

            if usages:
                return usages
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"Failed to parse template contexts: {e}")
            continue

    return None


def extract_execution_trace(
    root_span: OTLPSpan,
    span_hierarchy: dict[str, list[OTLPSpan]],
    project_id: UUID,
) -> dict[str, Any]:
    """
    Extract execution trace from OTLP span(s).

    Aggregates data from root span and its children:
    - Root span: agent_id, timing
    - Child spans: model, provider, template contexts (chat span has the real data)

    Args:
        root_span: The root execution span
        span_hierarchy: Dict mapping parent_span_id -> children (from build_span_hierarchy)
        project_id: Project UUID

    Returns:
        Dictionary ready for insertion into execution_traces table
    """
    attrs = root_span.attributes or {}

    # Extract core fields from root
    trace_id = root_span.trace_id
    session_id = attrs.get("dakora.session_id") or trace_id
    agent_id = attrs.get("gen_ai.agent.id")
    source = attrs.get("dakora.source", "maf")

    # Get child spans from hierarchy (O(1) lookup)
    child_spans = span_hierarchy.get(root_span.span_id, [])

    # Aggregate model and provider (prefer child span, fallback to root)
    model = None
    provider = None
    for span in [root_span] + child_spans:
        span_attrs = span.attributes or {}

        # Try to get model
        if not model:
            raw_model = (
                span_attrs.get("dakora.model")
                or span_attrs.get("gen_ai.response.model")
                or span_attrs.get("gen_ai.request.model")
            )
            model = normalize_model(raw_model)

        # Try to get provider
        if not provider:
            raw_provider = span_attrs.get("gen_ai.provider.name")
            provider = normalize_provider(raw_provider)

    # Aggregate metrics (prefer child span for accuracy, fallback to root)
    tokens_in = None
    tokens_out = None
    for span in child_spans + [root_span]:
        span_attrs = span.attributes or {}
        if tokens_in is None:
            tokens_in = span_attrs.get("gen_ai.usage.input_tokens")
        if tokens_out is None:
            tokens_out = span_attrs.get("gen_ai.usage.output_tokens")
        if tokens_in and tokens_out:
            break

    # Calculate latency (nanoseconds → milliseconds)
    latency_ms = int((root_span.end_time_ns - root_span.start_time_ns) / 1_000_000)

    # Cost calculation (simplified - will be None if model not found)
    cost_usd = None  # TODO: calculate from pricing table

    # Extract conversation history (try child spans first, then root)
    conversation_history = []
    for span in child_spans + [root_span]:
        conversation_history = extract_conversation_history(span)
        if conversation_history:
            break

    # Metadata - collect all dakora.* attributes (except reserved ones)
    metadata = {}
    reserved_keys = {
        "dakora.model", "dakora.template_contexts", "dakora.session_id", "dakora.source"
    }
    for key, value in attrs.items():
        if key.startswith("dakora.") and key not in reserved_keys:
            metadata[key[7:]] = value  # Strip "dakora." prefix

    return {
        "project_id": project_id,
        "trace_id": trace_id,
        "session_id": session_id,
        "parent_trace_id": root_span.parent_span_id,
        "agent_id": agent_id,
        "source": source,
        "conversation_history": conversation_history,
        "metadata": metadata if metadata else None,
        "provider": provider,
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
        # Legacy fields for backward compatibility
        "prompt_id": None,  # Will be set from template_usages
        "version": None,
        "inputs_json": None,
        "output_text": None,
        "cost": cost_usd,
    }