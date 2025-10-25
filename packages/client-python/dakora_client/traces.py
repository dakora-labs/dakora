"""Traces API client for managing execution traces and observability"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Dakora

logger = logging.getLogger("dakora_client.traces")


class TracesAPI:
    """API for managing execution traces and observability"""

    def __init__(self, client: "Dakora"):
        self._client = client

    async def create(
        self,
        project_id: str,
        trace_id: str,
        session_id: str,
        agent_id: str | None = None,
        parent_trace_id: str | None = None,
        template_usages: list[dict[str, Any]] | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        provider: str | None = None,
        model: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
        cost_usd: float | None = None,
    ) -> dict[str, Any]:
        """
        Create an execution trace entry.
        
        Args:
            project_id: Dakora project ID
            trace_id: Unique execution trace identifier
            session_id: Session/conversation identifier
            agent_id: Agent identifier (optional)
            parent_trace_id: Parent trace ID for nested calls (optional)
            template_usages: List of templates used in this execution
            conversation_history: Full conversation context
            metadata: Additional metadata (user_id, tags, etc.)
            provider: LLM provider (e.g., "openai", "anthropic")
            model: Model identifier (e.g., "gpt-4", "claude-3-opus")
            tokens_in: Input tokens count
            tokens_out: Output tokens count
            latency_ms: Execution latency in milliseconds
            cost_usd: Execution cost in USD
            
        Returns:
            Response with trace_id
            
        Example:
            >>> await dakora.traces.create(
            ...     project_id="proj-123",
            ...     trace_id="trace-456",
            ...     session_id="session-789",
            ...     agent_id="support-v1",
            ...     template_usages=[
            ...         {"prompt_id": "greeting", "version": "1.0.0", "inputs": {...}},
            ...     ],
            ...     tokens_in=150,
            ...     tokens_out=75,
            ...     cost_usd=0.00225,
            ... )
        """
        url = f"/api/projects/{project_id}/executions"

        payload: dict[str, Any] = {
            "trace_id": trace_id,
            "parent_trace_id": parent_trace_id,
            "session_id": session_id,
            "agent_id": agent_id,
            "template_usages": template_usages,
            "conversation_history": conversation_history,
            "metadata": metadata,
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
        }

        logger.debug(f"POST {url} (trace_id={trace_id})")
        response = await self._client.post(url, json=payload)
        logger.debug(f"POST {url} -> {response.status_code}")

        response.raise_for_status()
        result = response.json()
        logger.info(f"Created trace: {trace_id}")
        return result

    async def list(
        self,
        project_id: str,
        session_id: str | None = None,
        prompt_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        List execution traces with optional filters.
        
        Args:
            project_id: Dakora project ID
            session_id: Filter by session ID (optional)
            prompt_id: Filter by template ID (optional)
            agent_id: Filter by agent ID (optional)
            limit: Maximum number of results (default: 100)
            
        Returns:
            List of trace dictionaries
            
        Example:
            >>> # Get all traces for a session
            >>> traces = await dakora.traces.list(
            ...     project_id="proj-123",
            ...     session_id="session-789"
            ... )
            >>> 
            >>> # Get all traces using a specific template
            >>> traces = await dakora.traces.list(
            ...     project_id="proj-123",
            ...     prompt_id="greeting"
            ... )
        """
        url = f"/api/projects/{project_id}/executions"
        
        params: dict[str, Any] = {"limit": limit}
        if session_id:
            params["session_id"] = session_id
        if prompt_id:
            params["prompt_id"] = prompt_id
        if agent_id:
            params["agent_id"] = agent_id

        logger.debug(f"GET {url} with filters: {params}")
        response = await self._client.get(url, params=params)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        traces = response.json()
        logger.info(f"Listed {len(traces)} traces")
        return traces

    async def get(
        self,
        project_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Get trace details including full conversation.
        
        Args:
            project_id: Dakora project ID
            trace_id: Execution trace identifier
            
        Returns:
            Trace with conversation history and templates used
            
        Example:
            >>> trace = await dakora.traces.get(
            ...     project_id="proj-123",
            ...     trace_id="trace-456"
            ... )
            >>> print(trace["conversation_history"])
            >>> print(trace["templates_used"])
        """
        url = f"/api/projects/{project_id}/executions/{trace_id}"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        trace = response.json()
        logger.info(f"Retrieved trace: {trace_id}")
        return trace
