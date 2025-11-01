"""Observability middleware for Microsoft Agent Framework agents."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from agent_framework import ChatContext, ChatMiddleware, ChatMessage, ChatResponse, Role

if TYPE_CHECKING:
    from dakora_client import Dakora

__all__ = ["DakoraTraceMiddleware"]

logger = logging.getLogger(__name__)


class DakoraTraceMiddleware(ChatMiddleware):
    """
    Lightweight middleware that integrates Dakora with MAF's OTEL tracing.

    Responsibilities:
    - Check budget before execution (blocking if exceeded)

    OTEL handles everything else:
    - Agent ID tracking (gen_ai.agent.id)
    - Token tracking (gen_ai.usage.input_tokens/output_tokens)
    - Message capture (gen_ai.input.messages/output.messages)
    - Latency tracking (span duration)
    - Export to Dakora API via standard OTLP exporter
    """

    def __init__(
        self,
        dakora_client: Dakora,
        enable_budget_check: bool = False,
        budget_check_cache_ttl: int = 30,
    ) -> None:
        """
        Configure the middleware.

        Args:
            dakora_client: Dakora client instance with API key configured.
            enable_budget_check: Enable pre-execution budget checks (default: False).
                                When enabled, blocks execution if budget exceeded in strict mode.
                                Warning: Adds latency to every agent call.
            budget_check_cache_ttl: Cache TTL for budget checks in seconds (default: 30).
                                   Only used when enable_budget_check=True.
        """
        self.dakora = dakora_client
        self.enable_budget_check = enable_budget_check
        self.budget_check_cache_ttl = budget_check_cache_ttl
        self._budget_cache: dict[str, Any] | None = None
        self._budget_cache_time: datetime | None = None

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
            and (now - self._budget_cache_time).total_seconds()
            < self.budget_check_cache_ttl
        ):
            logger.debug(
                f"Using cached budget status "
                f"(age: {(now - self._budget_cache_time).total_seconds():.1f}s)"
            )
            return self._budget_cache

        # Fetch fresh budget status using Dakora client
        try:
            response = await self.dakora.get(f"/api/projects/{project_id}/budget")
            response.raise_for_status()
            budget_status = response.json()

            # Cache the result
            self._budget_cache = budget_status
            self._budget_cache_time = now

            return budget_status

        except Exception as e:
            logger.warning(f"Budget check failed: {e} - allowing execution (fail-open)")
            return {"exceeded": False, "status": "check_failed"}

    def _format_budget_error(self, budget_status: dict[str, Any]) -> ChatResponse:
        """
        Format user-friendly budget exceeded message.

        Args:
            budget_status: Budget status dictionary

        Returns:
            ChatResponse with error message
        """
        error_message = (
            f"❌ Budget Limit Reached\n\n"
            f"Your project has reached its monthly budget limit.\n\n"
            f"Budget: ${budget_status.get('budget_usd', 0):.2f}\n"
            f"Current Spend: ${budget_status.get('current_spend_usd', 0):.2f}\n\n"
            f"To continue:\n"
            f"1. Increase your budget in Dakora Studio Settings\n"
            f"2. Switch to 'alert' mode to allow executions with warnings\n"
            f"3. Wait until next month (budget resets on the 1st)"
        )

        return ChatResponse(
            messages=[
                ChatMessage(
                    role=Role.ASSISTANT,
                    text=error_message,
                )
            ]
        )

    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """
        Execute the downstream pipeline while checking budget and adding project context.

        OTEL (via MAF) automatically handles:
        - Creating span with agent_id, tokens, messages, etc.
        - Parent/child relationships for multi-agent scenarios
        - Exporting to configured OTEL backends
        """
        logger.debug("DakoraTraceMiddleware.process() called")

        # Check budget BEFORE execution (optional feature)
        if self.enable_budget_check:
            project_id = self.dakora.project_id

            if project_id:
                budget_status = await self._check_budget_with_cache(project_id)

                if budget_status.get("exceeded", False):
                    enforcement_mode = budget_status.get("enforcement_mode", "strict")

                    if enforcement_mode == "strict":
                        # STRICT MODE: Block execution
                        context.terminate = True
                        context.result = self._format_budget_error(budget_status)
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

        # Set dakora.* attributes on the current span (invoke_agent span)
        # This is simpler than creating a wrapper span and searching for it later
        try:
            from opentelemetry import trace

            # Get the current span (should be invoke_agent span created by MAF)
            current_span = trace.get_current_span()

            if current_span and current_span.is_recording():
                # Extract model from chat client
                client = getattr(context, "chat_client", None)
                if client:
                    model = getattr(client, "model_id", None) or getattr(client, "model", None)
                    if model:
                        current_span.set_attribute("dakora.model", model)
                        logger.debug(f"Set dakora.model={model} on current span")

                # Extract template contexts from messages
                messages = getattr(context, "messages", [])
                template_contexts = []
                for msg in messages:
                    dakora_ctx = getattr(msg, "_dakora_context", None)
                    if dakora_ctx and isinstance(dakora_ctx, dict):
                        template_contexts.append(dakora_ctx)

                if template_contexts:
                    current_span.set_attribute("dakora.template_contexts", json.dumps(template_contexts))
                    logger.debug(f"Set dakora.template_contexts with {len(template_contexts)} template(s) on current span")

        except ImportError:
            # OTEL not available
            logger.debug("OpenTelemetry not available")

        # Execute agent
        await next(context)

        # OTEL automatically:
        # - Captures tokens (gen_ai.usage.input_tokens, output_tokens)
        # - Captures messages (gen_ai.input.messages, output.messages)
        # - Captures agent_id (gen_ai.agent.id)
        # - Calculates latency (span duration)
        # - Exports to Dakora API via standard OTLP exporter