"""Helper functions for using Dakora with Agent Framework"""

from typing import TYPE_CHECKING

from agent_framework import ChatMessage, Role

if TYPE_CHECKING:
    from dakora_client.types import RenderResult


def to_message(
    render_result: "RenderResult",
    role: Role = Role.USER,
) -> ChatMessage:
    """
    Convert Dakora render result to Agent Framework message with metadata.
    
    This preserves template information for automatic linking by DakoraTraceMiddleware.
    The middleware extracts _dakora_context and creates template_executions records.
    
    Args:
        render_result: Result from dakora.prompts.render()
        role: Message role (default: USER)
    
    Returns:
        ChatMessage with attached template metadata
    
    Example:
        ```python
        from dakora_client import Dakora
        from dakora_af import to_message
        from agent_framework import ChatAgent, Role
        
        dakora = Dakora("https://api.dakora.io")
        
        # Render Dakora template
        greeting = await dakora.prompts.render(
            "customer-greeting",
            {"customer_name": "Alice", "tier": "premium"}
        )
        
        # Convert to AF message (preserves template metadata)
        message = to_message(greeting, role=Role.SYSTEM)
        
        # Use in agent
        agent = ChatAgent(...)
        result = await agent.run([message, ...])
        
        # ✅ Execution linked to "customer-greeting" template in Dakora Studio
        ```
    """
    message = ChatMessage(role=role, text=render_result.text)
    
    # Attach Dakora metadata to message for middleware extraction
    # This is read by DakoraTraceMiddleware.process() to create template linkage
    message._dakora_context = {
        "prompt_id": render_result.prompt_id,
        "version": render_result.version,
        "inputs": render_result.inputs,
        "metadata": render_result.metadata,
    }
    
    return message
