"""Observability middleware for Microsoft Agent Framework agents."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Final

import httpx
from agent_framework import ChatContext, ChatMiddleware, ChatMessage, ChatResponse, Role
from dakora_client import Dakora

if TYPE_CHECKING:
    from dakora_client.types import RenderResult

__all__ = ["DakoraTraceMiddleware", "create_dakora_middleware"]

logger = logging.getLogger(__name__)

TRACE_SOURCE: Final[str] = "maf"
TRACE_ID_METADATA_KEY: Final[str] = "dakora_trace_id"
SESSION_ID_METADATA_KEY: Final[str] = "dakora_session_id"
PARENT_TRACE_METADATA_KEY: Final[str] = "dakora_parent_trace_id"
AGENT_ID_METADATA_KEY: Final[str] = "dakora_agent_id"
EXTRA_METADATA_KEY: Final[str] = "dakora_metadata"
PROVIDER_ALIASES: Final[dict[str, str]] = {
    "AzureOpenAIChatClient": "azure",
    "OpenAIChatClient": "openai",
}

TemplateUsage = dict[str, Any]


class DakoraTraceMiddleware(ChatMiddleware):
    """Chat middleware that records Microsoft Agent Framework executions in Dakora."""

    def __init__(
        self,
        dakora_client: Dakora,
        session_id: str | None = None,
        instruction_template: dict[str, Any] | RenderResult | None = None,
        *,
        project_id: str | None = None,
        agent_id: str | None = None,
        parent_trace_id: str | None = None,
        budget_check_cache_ttl: int = 30,
    ) -> None:
        """
        Configure the middleware.

        Args:
            dakora_client: Dakora client instance used to send traces.
            session_id: Optional conversation/session identifier. Auto-generated when
                omitted.
            instruction_template: Optional template usage information for agent
                instructions. Supports either a RenderResult or the dictionary payload
                accepted by the traces API.
            project_id: Optional project override. Defaults to the client project.
            agent_id: Static agent identifier applied to all traces.
            parent_trace_id: Optional parent trace identifier for trace linking.
            budget_check_cache_ttl: Cache TTL for budget checks in seconds (default: 30).
        """
        self.dakora = dakora_client
        self.project_id = project_id or getattr(dakora_client, "project_id", None)
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())
        self.parent_trace_id = parent_trace_id
        self.last_trace_id: str | None = None
        self.budget_check_cache_ttl = budget_check_cache_ttl
        self._budget_cache: dict[str, Any] | None = None
        self._budget_cache_time: datetime | None = None
        self.instruction_template = self._normalize_template_usage(
            instruction_template,
            default_role="system",
            source="instruction",
            message_index=None,
        )

    def _prepare_agent_metadata(
        self,
        context: ChatContext,
        provider_hint: str | None,
    ) -> tuple[str | None, str | None, dict[str, Any] | None]:
        """Extract and normalise agent metadata from the chat context."""
        chat_options = getattr(context, "chat_options", None)
        agent_metadata = (
            getattr(chat_options, "metadata", None) if chat_options is not None else None
        )
        agent_id = self.agent_id
        parent_trace_id = self.parent_trace_id

        if not isinstance(context.metadata, dict):
            context.metadata = {}

        if not isinstance(agent_metadata, dict) or not agent_metadata:
            if agent_id:
                context.metadata.setdefault(AGENT_ID_METADATA_KEY, agent_id)
            if parent_trace_id:
                context.metadata.setdefault(PARENT_TRACE_METADATA_KEY, parent_trace_id)
            return agent_id, parent_trace_id, None

        agent_id = agent_metadata.get(AGENT_ID_METADATA_KEY) or agent_id
        metadata_parent = agent_metadata.get(PARENT_TRACE_METADATA_KEY)
        if metadata_parent:
            parent_trace_id = metadata_parent or parent_trace_id

        sanitized_metadata = dict(agent_metadata)
        sanitized_metadata.pop(AGENT_ID_METADATA_KEY, None)
        sanitized_metadata.pop(PARENT_TRACE_METADATA_KEY, None)

        if isinstance(context.metadata, dict):
            if sanitized_metadata:
                context.metadata.setdefault(EXTRA_METADATA_KEY, sanitized_metadata)
            if agent_id:
                context.metadata[AGENT_ID_METADATA_KEY] = agent_id
            if parent_trace_id:
                context.metadata[PARENT_TRACE_METADATA_KEY] = parent_trace_id

        should_strip = (
            provider_hint in {"openai", "azure"}
            and not bool(getattr(chat_options, "store", False))
        )
        if chat_options is not None:
            chat_options.metadata = None if should_strip else sanitized_metadata or None

        return agent_id, parent_trace_id, agent_metadata

    async def _check_budget_with_cache(self, project_id: str) -> dict[str, Any]:
        """
        Check budget with TTL-based caching to reduce latency.

        Cache prevents excessive API calls for high-frequency agents.

        Args:
            project_id: Project identifier

        Returns:
            Budget status dictionary
        """
        now = datetime.now()

        # Return cached result if still valid
        if (
            self._budget_cache is not None
            and self._budget_cache_time is not None
            and (now - self._budget_cache_time).total_seconds() < self.budget_check_cache_ttl
        ):
            logger.debug(
                f"Using cached budget status "
                f"(age: {(now - self._budget_cache_time).total_seconds():.1f}s)"
            )
            return self._budget_cache

        # Fetch fresh budget status
        try:
            base_url = getattr(self.dakora, "base_url", None) or getattr(self.dakora, "_base_url", None)
            api_key = getattr(self.dakora, "api_key", None) or getattr(self.dakora, "_api_key", None)

            if not base_url:
                logger.warning("Dakora base_url not found - skipping budget check")
                return {"exceeded": False, "status": "check_skipped"}

            async with httpx.AsyncClient(timeout=2.0) as client:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = await client.get(
                    f"{base_url}/api/projects/{project_id}/budget",
                    headers=headers,
                )
                response.raise_for_status()
                budget_status = response.json()

            # Cache the result
            self._budget_cache = budget_status
            self._budget_cache_time = now

            return budget_status

        except httpx.TimeoutException:
            logger.warning("Budget check timeout - allowing execution (fail-open)")
            return {"exceeded": False, "status": "check_timeout"}
        except Exception as e:
            logger.warning(f"Budget check failed: {e} - allowing execution (fail-open)")
            return {"exceeded": False, "status": "check_failed"}

    def _format_budget_error(self, budget_status: dict[str, Any]) -> str:
        """Format user-friendly budget exceeded message.

        Args:
            budget_status: Budget status dictionary

        Returns:
            Formatted error message
        """
        return (
            f"❌ Budget Limit Reached\n\n"
            f"Your project has reached its monthly budget limit.\n\n"
            f"Budget: ${budget_status.get('budget_usd', 0):.2f}\n"
            f"Current Spend: ${budget_status.get('current_spend_usd', 0):.2f}\n\n"
            f"To continue:\n"
            f"1. Increase your budget in Dakora Studio Settings\n"
            f"2. Switch to 'alert' mode to allow executions with warnings\n"
            f"3. Wait until next month (budget resets on the 1st)"
        )

    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """Execute the downstream pipeline while capturing trace metadata."""
        project_id = self.project_id or getattr(self.dakora, "project_id", None)
        agent_id = self.agent_id
        parent_trace_id = self.parent_trace_id

        client = getattr(context, "chat_client", None)
        client_class_name = type(client).__name__ if client else None
        provider_hint = self._extract_provider_from_client(client_class_name)

        chat_options = getattr(context, "chat_options", None)
        agent_id_override, parent_override, original_metadata = self._prepare_agent_metadata(
            context, provider_hint
        )
        if agent_id_override is not None:
            agent_id = agent_id_override or agent_id
        if parent_override is not None:
            parent_trace_id = parent_override or parent_trace_id

        if not isinstance(context.metadata, dict):
            context.metadata = {}

        metadata_parent = context.metadata.get(PARENT_TRACE_METADATA_KEY)
        if metadata_parent:
            parent_trace_id = metadata_parent

        trace_id = str(uuid.uuid4())
        self.last_trace_id = trace_id
        context.metadata[TRACE_ID_METADATA_KEY] = trace_id
        context.metadata[SESSION_ID_METADATA_KEY] = self.session_id
        if parent_trace_id:
            context.metadata[PARENT_TRACE_METADATA_KEY] = parent_trace_id
        else:
            context.metadata.pop(PARENT_TRACE_METADATA_KEY, None)

        # 🆕 CHECK BUDGET BEFORE EXECUTION
        if project_id:
            budget_status = await self._check_budget_with_cache(project_id)

            if budget_status.get("exceeded", False):
                enforcement_mode = budget_status.get("enforcement_mode", "strict")

                if enforcement_mode == "strict":
                    # STRICT MODE: Block execution
                    context.terminate = True
                    context.result = ChatResponse(
                        messages=[
                            ChatMessage(
                                role=Role.ASSISTANT,
                                text=self._format_budget_error(budget_status),
                            )
                        ]
                    )
                    logger.warning(
                        f"Execution BLOCKED: Budget exceeded for project {project_id} "
                        f"(${budget_status.get('current_spend_usd', 0):.2f} / "
                        f"${budget_status.get('budget_usd', 0):.2f})"
                    )
                    return  # Exit early - no LLM call

                elif enforcement_mode == "alert":
                    # ALERT MODE: Log warning but allow execution
                    logger.warning(
                        f"Budget EXCEEDED but allowing execution (alert mode): "
                        f"Project {project_id} "
                        f"(${budget_status.get('current_spend_usd', 0):.2f} / "
                        f"${budget_status.get('budget_usd', 0):.2f})"
                    )

            elif budget_status.get("status") == "warning":
                # At warning threshold
                logger.info(
                    f"Budget WARNING: Project {project_id} at "
                    f"{budget_status.get('percentage_used', 0):.1f}% "
                    f"(${budget_status.get('current_spend_usd', 0):.2f} / "
                    f"${budget_status.get('budget_usd', 0):.2f})"
                )

        start_time = perf_counter()

        template_usages: list[TemplateUsage] = []
        if self.instruction_template:
            template_usages.append(self.instruction_template)

        try:
            await next(context)
        finally:
            if chat_options is not None and original_metadata is not None:
                chat_options.metadata = original_metadata

        latency_ms = int((perf_counter() - start_time) * 1000)

        conversation_history, message_template_usages = self._build_conversation_history(
            context
        )
        if message_template_usages:
            template_usages.extend(message_template_usages)

        tokens_in = None
        tokens_out = None
        if context.result and hasattr(context.result, "usage_details"):
            usage = context.result.usage_details
            tokens_in = getattr(usage, "input_token_count", None)
            tokens_out = getattr(usage, "output_token_count", None)

        provider = None
        if client is not None:
            for attr in ("provider", "provider_name", "api_type"):
                value = getattr(client, attr, None)
                if isinstance(value, str) and value:
                    provider = value.lower()
                    break
        if provider is None:
            provider = provider_hint

        model = None
        if client is not None:
            model = getattr(client, "model_id", None) or getattr(client, "model", None)
        if not model and context.result and hasattr(context.result, "model_id"):
            model = context.result.model_id

        context_metadata = getattr(context, "metadata", None)
        metadata = dict(context_metadata) if isinstance(context_metadata, dict) else None

        asyncio.create_task(
            self._send_trace(
                project_id=project_id,
                agent_id=agent_id,
                trace_id=trace_id,
                parent_trace_id=parent_trace_id,
                template_usages=template_usages or None,
                conversation_history=conversation_history,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                metadata=metadata,
                source=TRACE_SOURCE,
            )
        )

    def _extract_provider_from_client(self, client_class_name: str | None) -> str | None:
        """Infer the provider name from a chat client class name."""
        if not client_class_name:
            return None

        for class_name, provider in PROVIDER_ALIASES.items():
            if class_name in client_class_name:
                return provider

        return None

    async def _send_trace(
        self,
        *,
        project_id: str | None,
        agent_id: str | None,
        trace_id: str,
        parent_trace_id: str | None,
        template_usages: list[TemplateUsage] | None,
        conversation_history: list[dict[str, Any]],
        provider: str | None,
        model: str | None,
        latency_ms: int,
        tokens_in: int | None,
        tokens_out: int | None,
        metadata: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> None:
        """Send the captured execution details to Dakora's traces endpoint."""
        if not project_id:
            logger.warning("Cannot send trace to Dakora: project_id not configured")
            return

        try:
            await self.dakora.traces.create(
                project_id=project_id,
                trace_id=trace_id,
                session_id=self.session_id,
                agent_id=agent_id,
                parent_trace_id=parent_trace_id,
                source=source,
                template_usages=template_usages,
                conversation_history=conversation_history,
                metadata=metadata,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            logger.debug("Logged execution %s to Dakora", trace_id)
        except Exception as exc:
            logger.warning("Failed to log execution to Dakora: %s", exc)

    def _normalize_template_usage(
        self,
        template: dict[str, Any] | RenderResult | None,
        *,
        default_role: str | None,
        source: str,
        message_index: int | None,
    ) -> TemplateUsage | None:
        """Convert a render result or dict into a template usage payload."""
        if template is None:
            return None

        if hasattr(template, "prompt_id") and hasattr(template, "version"):
            base = {
                "prompt_id": getattr(template, "prompt_id"),
                "version": getattr(template, "version"),
                "inputs": getattr(template, "inputs", {}) or {},
                "metadata": getattr(template, "metadata", {}) or {},
            }
        elif isinstance(template, dict):
            prompt_id = template.get("prompt_id")
            version = template.get("version")
            if not prompt_id or not version:
                logger.debug(
                    "Skipping template without prompt_id/version: %s", template
                )
                return None
            base = {
                "prompt_id": prompt_id,
                "version": version,
                "inputs": template.get("inputs", {}) or {},
                "metadata": template.get("metadata", {}) or {},
            }
        else:
            logger.debug("Unsupported template type for normalization: %s", type(template))
            return None

        role = base.get("role") or default_role
        return {
            **base,
            "role": role,
            "source": source,
            "message_index": message_index,
        }

    def _build_conversation_history(
        self,
        context: ChatContext,
    ) -> tuple[list[dict[str, Any]], list[TemplateUsage]]:
        """Collect the full conversation history and any template usage metadata."""
        history: list[dict[str, Any]] = []
        template_usages: list[TemplateUsage] = []

        def _record_message(msg: Any) -> None:
            role = getattr(msg.role, "value", None) or str(getattr(msg, "role", ""))
            content = getattr(msg, "text", None)
            if content is None:
                content = getattr(msg, "contents", None)
            if content is None:
                content = str(msg)

            index = len(history)
            template_ctx = getattr(msg, "_dakora_context", None)
            history.append(
                {
                    "index": index,
                    "role": role,
                    "content": content,
                    "dakora_template": template_ctx,
                }
            )

            if isinstance(template_ctx, dict):
                normalized = self._normalize_template_usage(
                    template_ctx,
                    default_role=role,
                    source="message",
                    message_index=index,
                )
                if normalized:
                    template_usages.append(normalized)

        for message in getattr(context, "messages", []):
            _record_message(message)

        result_messages = getattr(getattr(context, "result", None), "messages", None)
        if result_messages:
            for message in result_messages:
                _record_message(message)

        return history, template_usages

    def set_parent_trace_id(self, parent_trace_id: str | None) -> None:
        """Update the parent trace identifier for subsequent middleware runs."""
        self.parent_trace_id = parent_trace_id


def create_dakora_middleware(
    dakora_client: Dakora,
    *,
    project_id: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
    instruction_template: dict[str, Any] | RenderResult | None = None,
    instruction: RenderResult | None = None,
    parent_trace_id: str | None = None,
    budget_check_cache_ttl: int = 30,
) -> DakoraTraceMiddleware:
    """Convenience factory for :class:`DakoraTraceMiddleware` instances.

    Args:
        dakora_client: Dakora client instance.
        project_id: Optional project override.
        agent_id: Static agent identifier.
        session_id: Optional conversation/session identifier.
        instruction_template: Optional template usage information (deprecated, use instruction).
        instruction: Optional template usage information for agent instructions.
        parent_trace_id: Optional parent trace identifier.
        budget_check_cache_ttl: Cache TTL for budget checks in seconds (default: 30).

    Returns:
        Configured DakoraTraceMiddleware instance.
    """
    if instruction is not None and instruction_template is not None:
        logger.warning(
            "Both 'instruction' and 'instruction_template' were provided to create_dakora_middleware; preferring 'instruction'."
        )

    template_input = instruction if instruction is not None else instruction_template

    return DakoraTraceMiddleware(
        dakora_client=dakora_client,
        session_id=session_id,
        instruction_template=template_input,
        project_id=project_id,
        agent_id=agent_id,
        parent_trace_id=parent_trace_id,
        budget_check_cache_ttl=budget_check_cache_ttl,
    )
