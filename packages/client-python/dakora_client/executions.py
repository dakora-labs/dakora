"""Executions API client for querying agent execution history.

Note: Execution data is automatically sent via OTLP (OpenTelemetry) from agent frameworks.
This API is for read-only querying of execution history.
"""

import logging
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from .client import Dakora

logger = logging.getLogger("dakora_client.executions")


class ExecutionListResponse(TypedDict):
    """Response from list executions endpoint with pagination metadata"""
    executions: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class ExecutionsAPI:
    """API for querying agent execution history.

    Execution data is automatically collected via OTLP (OpenTelemetry) when using
    dakora-agents with agent frameworks like Microsoft Agent Framework.

    This API provides read-only access to execution history for analytics and debugging.
    """

    def __init__(self, client: "Dakora"):
        self._client = client

    async def list(
        self,
        project_id: str,
        session_id: str | None = None,
        prompt_id: str | None = None,
        agent_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        include_metadata: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        List agent executions with optional filters.

        Args:
            project_id: Dakora project ID
            session_id: Filter by session ID (optional)
            prompt_id: Filter by template ID (optional)
            agent_id: Filter by agent ID (optional)
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)
            include_metadata: If True, return dict with executions, total, limit, offset.
                             If False, return just the executions list (default: False)

        Returns:
            If include_metadata=False: List of execution dictionaries
            If include_metadata=True: Dict with keys: executions, total, limit, offset

        Example:
            >>> # Get all executions for a session
            >>> executions = await dakora.executions.list(
            ...     project_id="proj-123",
            ...     session_id="session-789"
            ... )
            >>> print(f"Got {len(executions)} executions")
            >>>
            >>> # Get executions with pagination metadata
            >>> result = await dakora.executions.list(
            ...     project_id="proj-123",
            ...     limit=25,
            ...     offset=0,
            ...     include_metadata=True
            ... )
            >>> print(f"Showing {len(result['executions'])} of {result['total']} executions")
        """
        url = f"/api/projects/{project_id}/executions"

        params: dict[str, Any] = {"limit": limit, "offset": offset}
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
        data = response.json()
        executions = data.get("executions", [])
        total = data.get("total", 0)
        logger.info(f"Listed {len(executions)} executions (total: {total})")

        if include_metadata:
            return data
        return executions

    async def get(
        self,
        project_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        """
        Get execution details including full conversation.

        Args:
            project_id: Dakora project ID
            execution_id: Execution identifier (trace_id from OTLP)

        Returns:
            Execution with conversation history and templates used

        Example:
            >>> execution = await dakora.executions.get(
            ...     project_id="proj-123",
            ...     execution_id="trace-456"
            ... )
            >>> print(execution["conversation_history"])
            >>> print(execution["templates_used"])
        """
        url = f"/api/projects/{project_id}/executions/{execution_id}"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        execution = response.json()
        logger.info(f"Retrieved execution: {execution_id}")
        return execution