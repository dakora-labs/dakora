"""DakoraTraceMiddleware for Microsoft Agent Framework observability"""

import time
import logging
import uuid
from typing import Optional, TYPE_CHECKING, Callable, Awaitable

from agent_framework import ChatMiddleware, ChatContext

if TYPE_CHECKING:
    from dakora_client import Dakora

logger = logging.getLogger(__name__)


class DakoraTraceMiddleware(ChatMiddleware):
    """
    ChatMiddleware that logs all LLM calls to Dakora with optional template linking.
    
    This middleware provides automatic observability for Agent Framework agents,
    tracking tokens, latency, and full conversation history. It works
    with or without Dakora templates - you get observability either way!
    
    Supported Providers:
    - ✅ OpenAI (via OpenAIChatClient)
    - ✅ Azure OpenAI (via AzureOpenAIChatClient)
    
    Features:
    - ✅ Automatic token counting and cost calculation
    - ✅ Session tracking for multi-agent workflows
    - ✅ Template linkage when using Dakora prompts
    - ✅ Full conversation history capture
    - ✅ Non-blocking async logging (won't slow down your agents)
    
    Example 1: Observability only (no templates):
        ```python
        from dakora_client import Dakora
        from dakora_af import DakoraTraceMiddleware
        from agent_framework import ChatAgent
        from agent_framework.openai import OpenAIChatClient
        
        dakora = Dakora("https://api.dakora.io", api_key="dk_xxx")
        
        agent = ChatAgent(
            chat_client=OpenAIChatClient(),
            instructions="You are a helpful assistant.",
            middleware=[DakoraTraceMiddleware(
                dakora,
                project_id="support-bot",
                agent_id="support-v1",
            )],
        )
        
        result = await agent.run("I need help")
        # ✅ Automatically tracked in Dakora Studio
        ```
    
    Example 2: With Dakora templates:
        ```python
        from dakora_af import DakoraTraceMiddleware, to_message
        
        # Render Dakora template
        greeting = await dakora.prompts.render(
            "customer-greeting",
            {"customer_name": "Alice", "tier": "premium"}
        )
        
        # Create middleware (same session for multi-turn)
        middleware = DakoraTraceMiddleware(
            dakora,
            project_id="support-bot",
            session_id="user-session-123",
        )
        
        agent = ChatAgent(
            chat_client=OpenAIChatClient(),
            instructions="You are a helpful support agent.",
            middleware=[middleware],
        )
        
        # Convert to AF message (preserves template metadata)
        result = await agent.run([
            to_message(greeting, role=Role.SYSTEM),
            ChatMessage(role=Role.USER, text="I need help"),
        ])
        # ✅ Linked to template "customer-greeting" in Dakora Studio
        ```
    """
    
    def __init__(
        self,
        dakora_client: "Dakora",
        project_id: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Initialize Dakora tracing middleware.
        
        Args:
            dakora_client: Dakora client instance
            project_id: Dakora project ID
            agent_id: Agent identifier (optional)
            session_id: Session/conversation ID (auto-generated if not provided)
        """
        self.dakora = dakora_client
        self.project_id = project_id
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())
    
    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """
        Process chat request and log to Dakora.
        
        Captures metrics before and after LLM execution, then asynchronously
        logs to Dakora without blocking the agent.
        """
        # Generate unique trace ID for this execution
        trace_id = str(uuid.uuid4())
        
        # Store in context for downstream use
        context.metadata["dakora_trace_id"] = trace_id
        context.metadata["dakora_session_id"] = self.session_id
        
        # Capture start time
        start_time = time.time()
        
        # Extract Dakora template info from messages (if any)
        template_usages = []
        for msg in context.messages:
            if hasattr(msg, "_dakora_context"):
                template_usages.append({
                    "prompt_id": msg._dakora_context["prompt_id"],
                    "version": msg._dakora_context["version"],
                    "inputs": msg._dakora_context["inputs"],
                    "metadata": msg._dakora_context.get("metadata", {}),
                })
        
        # Execute the actual LLM call
        await next(context)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Extract conversation history
        conversation_history = [
            {
                "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                "content": msg.text or str(msg.contents) if hasattr(msg, "contents") else str(msg),
                "dakora_template": getattr(msg, "_dakora_context", None),
            }
            for msg in context.messages
        ]
        
        # Add assistant response to conversation history
        if context.result and hasattr(context.result, "messages"):
            for msg in context.result.messages:
                conversation_history.append({
                    "role": msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    "content": msg.text or str(msg.contents) if hasattr(msg, "contents") else str(msg),
                })
        
        # Extract usage info from response
        tokens_in = None
        tokens_out = None
        if context.result and hasattr(context.result, "usage_details"):
            usage = context.result.usage_details
            tokens_in = usage.input_token_count if hasattr(usage, "input_token_count") else None
            tokens_out = usage.output_token_count if hasattr(usage, "output_token_count") else None
        
        # Extract provider and model
        # The chat client itself is stored in context, not chat_options
        client_class_name = type(context.chat_client).__name__ if hasattr(context, "chat_client") else None
        provider = self._extract_provider_from_client(client_class_name)
        
        # The model_id is stored on the client, not chat_options
        model = None
        if hasattr(context, "chat_client") and hasattr(context.chat_client, "model_id"):
            model = context.chat_client.model_id
        
        # Fallback: try to get model from response (ChatResponse.model_id)
        if not model and context.result and hasattr(context.result, "model_id"):
            model = context.result.model_id
        
        # Log to Dakora (async, non-blocking)
        try:
            await self.dakora.traces.create(
                project_id=self.project_id,
                trace_id=trace_id,
                session_id=self.session_id,
                agent_id=self.agent_id,
                template_usages=template_usages if template_usages else None,
                conversation_history=conversation_history,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            logger.debug(f"Logged execution {trace_id} to Dakora")
        except Exception as e:
            # Don't fail the request if logging fails
            logger.warning(f"Failed to log execution to Dakora: {e}")
    
    def _extract_provider_from_client(self, client_class_name: Optional[str]) -> Optional[str]:
        """
        Extract provider name from chat client class name.
        
        Maps chat client class names to provider identifiers.
        Currently supports Microsoft Agent Framework's OpenAI and Azure OpenAI implementations.
        """
        if not client_class_name:
            return None
        
        # Map client class names to providers
        # Note: Order matters! Check more specific names first (Azure before OpenAI)
        provider_map = {
            "AzureOpenAIChatClient": "azure",
            "OpenAIChatClient": "openai",
        }
        
        for class_name, provider in provider_map.items():
            if class_name in client_class_name:
                return provider
        
        return None


def create_dakora_middleware(
    dakora_client: "Dakora",
    project_id: str,
    agent_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> DakoraTraceMiddleware:
    """
    Convenience factory function to create DakoraTraceMiddleware.
    
    Args:
        dakora_client: Dakora client instance
        project_id: Dakora project ID
        agent_id: Agent identifier (optional)
        session_id: Session/conversation ID (optional, auto-generated)
    
    Returns:
        Configured DakoraTraceMiddleware instance
    
    Example:
        ```python
        from dakora_af import create_dakora_middleware
        
        middleware = create_dakora_middleware(
            dakora_client=dakora,
            project_id="support-bot",
            agent_id="support-v1",
        )
        
        agent = ChatAgent(
            chat_client=OpenAIChatClient(),
            middleware=[middleware],
        )
        ```
    """
    return DakoraTraceMiddleware(
        dakora_client=dakora_client,
        project_id=project_id,
        agent_id=agent_id,
        session_id=session_id,
    )
