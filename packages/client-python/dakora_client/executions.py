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
        prompt_id: str | None = None,
        agent_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        has_templates: bool | None = None,
        min_cost: float | None = None,
        start: str | None = None,
        end: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        limit: int = 100,
        offset: int = 0,
        include_metadata: bool = False,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """
        List agent executions with optional filters.

        Args:
            project_id: Dakora project ID
            prompt_id: Filter by template ID (optional)
            agent_id: Filter by agent ID (optional)
            provider: Filter by provider (optional)
            model: Filter by model (optional)
            has_templates: Filter by presence of template linkages (optional)
            min_cost: Filter by minimum cost threshold in USD (optional)
            start: Filter by start date/time ISO format (optional)
            end: Filter by end date/time ISO format (optional)
            page: Page number for pagination (optional, alternative to offset)
            page_size: Number of items per page (optional, alternative to limit)
            limit: Maximum number of results (default: 100)
            offset: Pagination offset (default: 0)
            include_metadata: If True, return dict with executions, total, limit, offset.
                             If False, return just the executions list (default: False)

        Returns:
            If include_metadata=False: List of execution dictionaries
            If include_metadata=True: Dict with keys: executions, total, limit, offset

        Example:
            >>> # Get all executions for a project
            >>> executions = await dakora.executions.list(
            ...     project_id="proj-123",
            ...     agent_id="agent-1"
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
            >>>
            >>> # Filter by templates and cost
            >>> executions = await dakora.executions.list(
            ...     project_id="proj-123",
            ...     has_templates=True,
            ...     min_cost=0.01
            ... )
        """
        url = f"/api/projects/{project_id}/executions"

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if prompt_id:
            params["prompt_id"] = prompt_id
        if agent_id:
            params["agent_id"] = agent_id
        if provider:
            params["provider"] = provider
        if model:
            params["model"] = model
        if has_templates is not None:
            params["has_templates"] = str(has_templates).lower()
        if min_cost is not None:
            params["min_cost"] = min_cost
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size

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
        trace_id: str,
        span_id: str | None = None,
        include_messages: bool = False,
    ) -> dict[str, Any]:
        """
        Get execution details including full conversation.

        Args:
            project_id: Dakora project ID
            trace_id: Execution identifier (trace_id)
            span_id: Optional specific span id
            include_messages: Include full input/output messages (default: False for performance)

        Returns:
            Execution with conversation history and templates used

        Example:
            >>> execution = await dakora.executions.get(
            ...     project_id="proj-123",
            ...     execution_id="trace-456",
            ...     include_messages=True
            ... )
            >>> print(execution["conversation_history"])
            >>> print(execution["templates_used"])
        """
        url = f"/api/projects/{project_id}/executions/{trace_id}"

        logger.debug(f"GET {url}")
        params = {}
        if span_id:
            params["span_id"] = span_id
        if include_messages:
            params["include_messages"] = "true"
        response = await self._client.get(url, params=params if params else None)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        execution = response.json()
        logger.info(f"Retrieved execution: {trace_id}")
        return execution

    async def get_related(
        self,
        project_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Get related traces (same session/parent trace).

        Args:
            project_id: Dakora project ID
            trace_id: Execution identifier (trace_id)

        Returns:
            Related traces information including session traces and parent/child relationships

        Example:
            >>> related = await dakora.executions.get_related(
            ...     project_id="proj-123",
            ...     trace_id="trace-456"
            ... )
            >>> print(f"Found {len(related.get('session_traces', []))} related traces")
        """
        url = f"/api/projects/{project_id}/executions/{trace_id}/related"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        related = response.json()
        logger.info(f"Retrieved related traces for: {trace_id}")
        return related

    async def get_hierarchy(
        self,
        project_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Get execution hierarchy (tree view of spans).

        Args:
            project_id: Dakora project ID
            trace_id: Execution identifier (trace_id)

        Returns:
            Hierarchical tree structure of execution spans

        Example:
            >>> hierarchy = await dakora.executions.get_hierarchy(
            ...     project_id="proj-123",
            ...     trace_id="trace-456"
            ... )
            >>> print(f"Root span: {hierarchy.get('span_id')}")
        """
        url = f"/api/projects/{project_id}/executions/{trace_id}/hierarchy"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        hierarchy = response.json()
        logger.info(f"Retrieved hierarchy for: {trace_id}")
        return hierarchy

    async def get_timeline(
        self,
        project_id: str,
        trace_id: str,
        compact_tools: bool = True,
    ) -> dict[str, Any]:
        """
        Get normalized timeline view of execution (unified conversation + tools).

        This is the new unified timeline view that combines messages and tool calls
        into a single chronological sequence.

        Args:
            project_id: Dakora project ID
            trace_id: Execution identifier (trace_id)
            compact_tools: If True, collapse tool_call+tool_result pairs into single events (default: True)

        Returns:
            Timeline response with events list containing normalized timeline items

        Example:
            >>> timeline = await dakora.executions.get_timeline(
            ...     project_id="proj-123",
            ...     trace_id="trace-456",
            ...     compact_tools=True
            ... )
            >>> events = timeline.get("events", [])
            >>> print(f"Timeline has {len(events)} events")
        """
        url = f"/api/projects/{project_id}/executions/{trace_id}/timeline"

        params = {}
        if compact_tools:
            params["compact_tools"] = "true"

        logger.debug(f"GET {url}")
        response = await self._client.get(url, params=params if params else None)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        timeline = response.json()
        logger.info(f"Retrieved timeline for: {trace_id}")
        return timeline
