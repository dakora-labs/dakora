"""Helper utilities for integrating Dakora with Microsoft Agent Framework."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, Protocol, runtime_checkable

from agent_framework import ChatMessage, Role

if TYPE_CHECKING:
    from dakora_client.types import RenderResult

__all__ = ["to_message", "to_instruction_template"]

DAKORA_CONTEXT_ATTR: Final[str] = "_dakora_context"


@runtime_checkable
class _SupportsTemplateContext(Protocol):
    """Structural type describing the render result data we rely on."""

    text: str
    prompt_id: str
    version: str
    inputs: dict[str, Any]
    metadata: dict[str, Any]

    def to_template_usage(
        self,
        *,
        role: str | None = "system",
        source: str = "instruction",
        message_index: int | None = None,
    ) -> dict[str, Any]:
        ...


def to_message(
    render_result: _SupportsTemplateContext,
    role: Role = Role.USER,
) -> ChatMessage:
    """
    Convert a Dakora render result into a Microsoft Agent Framework message.

    The returned message contains the rendered text and embeds Dakora metadata so
    :class:`~dakora_agents.maf.middleware.DakoraTraceMiddleware` can automatically
    associate the execution with the originating template.
    """
    message = ChatMessage(role=role, text=render_result.text)

    dakora_context = {
        "prompt_id": render_result.prompt_id,
        "version": render_result.version,
        "inputs": dict(render_result.inputs or {}),
        "metadata": dict(render_result.metadata or {}),
    }
    setattr(message, DAKORA_CONTEXT_ATTR, dakora_context)  # type: ignore[attr-defined]

    return message


def to_instruction_template(render_result: _SupportsTemplateContext) -> dict[str, Any]:
    """
    Build a template usage payload from a render result for agent instructions.

    This delegates to :meth:`dakora_client.types.RenderResult.to_template_usage`
    so middleware callers do not need to handcraft the payload.
    """
    return render_result.to_template_usage(
        role="system",
        source="instruction",
        message_index=None,
    )
