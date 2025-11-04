"""Type definitions for Dakora client SDK"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, cast


@dataclass
class RenderResult:
    """
    Result of rendering a template with execution context.
    
    This object wraps the rendered prompt text along with metadata
    that enables automatic template linkage when used with dakora-af middleware.
    
    Attributes:
        text: The rendered prompt text
        prompt_id: Template identifier
        version: Template version used
        inputs: Input variables used for rendering
        metadata: Additional metadata (user_id, tags, etc.)
    
    Example:
        >>> result = await dakora.prompts.render("greeting", {"name": "Alice"})
        >>> print(result.text)
        "Hello Alice!"
        >>> result.with_metadata(user_id="user-123")
    """
    
    text: str
    prompt_id: str
    version: str
    inputs: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=lambda: cast(dict[str, Any], {}))