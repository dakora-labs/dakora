"""Type definitions for Dakora client SDK"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


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
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> RenderResult:
        """
        Add additional metadata to the render result.
        
        This method returns self to allow chaining.
        
        Args:
            **kwargs: Key-value pairs to add to metadata
            
        Returns:
            Self for method chaining
            
        Example:
            >>> result.with_metadata(user_id="user-123", session="abc")
        """
        self.metadata.update(kwargs)
        return self

    def to_message(self, role: str = "user") -> Any:
        """
        Convert rendered result to a Microsoft Agent Framework message with Dakora tracking.
        
        This creates a ChatMessage with embedded metadata that allows the dakora-agents 
        middleware to automatically link the execution trace back to this specific 
        template and version.
        
        Args:
            role: Message role - "user" or "system" (default: "user")
        
        Returns:
            A ChatMessage object compatible with Microsoft Agent Framework
            
        Example:
            >>> result = await dakora.prompts.render("greeting", {"name": "Alice"})
            >>> message = result.to_message()
            >>> # Use in agent: await agent.run(message.text)
            
        Note:
            Requires agent-framework to be installed.
        """
        # Import here to avoid circular dependency and allow use without MAF installed
        try:
            from agent_framework import ChatMessage, Role
        except ImportError:
            raise ImportError(
                "agent-framework is required to use to_message(). "
                "Install with: pip install agent-framework"
            )
        
        # Map string role to Role enum
        role_enum = Role.USER if role.lower() == "user" else Role.SYSTEM
        
        # Create message with the rendered text
        msg = ChatMessage(role=role_enum, text=self.text)
        
        # Attach Dakora context as private attribute for middleware to detect
        msg._dakora_context = {  # type: ignore[attr-defined]
            "prompt_id": self.prompt_id,
            "version": self.version,
            "inputs": self.inputs,
            "metadata": self.metadata,
        }
        
        return msg

    def to_template_usage(
        self,
        *,
        role: str | None = "system",
        source: str = "instruction",
        message_index: int | None = None,
    ) -> dict[str, Any]:
        """
        Convert this render result into a template usage payload suitable for the traces API.
        
        Args:
            role: Optional role associated with the template (e.g., "system", "user").
            source: Logical source of the template (default: "instruction").
            message_index: Optional conversation index for correlating with history.
        
        Returns:
            Dictionary compatible with dakora.traces.create(template_usages=[...]).
        """
        return {
            "prompt_id": self.prompt_id,
            "version": self.version,
            "inputs": dict(self.inputs),
            "metadata": dict(self.metadata),
            "role": role,
            "source": source,
            "message_index": message_index,
        }
