
"""Dakora Platform Client"""

import os
import logging
import httpx
from typing import Any

logger = logging.getLogger("dakora_client")


class Dakora:
    """
    Dakora Platform Client

    Create once, reuse everywhere - just like OpenAI's client.

    Warning:
        Treat a Dakora instance like a credential. Sharing the object grants callers the ability
        to perform authenticated requests against your workspace. The API key is stored internally
        and cannot be read back once provided.

    Example:
        from dakora_client import Dakora

        # Create client once
        client = Dakora(api_key="dk_xxx")

        # Reuse for multiple calls
        templates = await client.prompts.list()
        result = await client.prompts.render("greeting", {"name": "Alice"})

        # FastAPI - initialize at startup
        from fastapi import FastAPI

        app = FastAPI()
        dakora = Dakora(api_key="dk_xxx")

        @app.get("/templates")
        async def get_templates():
            return await dakora.prompts.list()

        # Local development
        dakora = Dakora(base_url="http://localhost:8000")

        # Using environment variables (DAKORA_API_KEY, DAKORA_BASE_URL)
        dakora = Dakora()
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        project_id: str | None = None,
    ):
        """
        Initialize Dakora client

        Args:
            api_key: API key for authentication. Defaults to DAKORA_API_KEY environment variable.
            base_url: Base URL of the Dakora API server. Defaults to DAKORA_BASE_URL environment
                     variable, or https://api.dakora.io if not set.
            project_id: Project ID (optional). If not provided, will be fetched from /api/me/context.
        """
        api_key_value = api_key or os.getenv("DAKORA_API_KEY")
        self.__api_key: str | None = api_key_value
        self._base_url = (
            base_url or os.getenv("DAKORA_BASE_URL") or "https://api.dakora.io"
        ).rstrip("/")

        logger.debug(
            f"Initializing Dakora client: base_url={self.base_url}, "
            f"api_key={'present' if self.has_api_key() else 'none'}, "
            f"project_id={project_id or 'auto'}"
        )

        self.__http = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.__build_default_headers(),
            timeout=30.0,
        )

        # Fetch project_id synchronously during initialization if API key is present
        if project_id:
            self._project_id = project_id
        elif api_key_value:
            self._project_id = self._fetch_project_id_sync()
            logger.info(f"Project ID fetched during init: {self._project_id}")
        else:
            self._project_id = None

        # Import here to avoid circular dependency
        from .prompts import PromptsAPI
        from .executions import ExecutionsAPI

        self.prompts = PromptsAPI(self)
        self.executions = ExecutionsAPI(self)
        logger.info(f"Dakora client initialized for {self.base_url}")

    def _fetch_project_id_sync(self) -> str:
        """
        Synchronously fetch project_id from /api/me/context.

        Called during __init__ to eagerly load project_id.
        Uses synchronous httpx.Client for compatibility with sync contexts (e.g., OTEL exporters).
        """
        logger.debug("Fetching project_id from /api/me/context (sync)")
        try:
            with httpx.Client(base_url=self.base_url, timeout=5.0) as client:
                response = client.get(
                    "/api/me/context",
                    headers={"X-API-Key": self.__api_key} if self.__api_key else {},
                )
                response.raise_for_status()
                project_id = response.json()["project_id"]
                logger.debug(f"Project ID fetched: {project_id}")
                return project_id
        except Exception as e:
            logger.error(f"Failed to fetch project_id during initialization: {e}")
            raise

    async def _get_project_id(self) -> str:
        """Get project ID from user context (cached after first call)"""
        if self._project_id is None:
            logger.debug("Fetching project context from /api/me/context")
            response = await self.get("/api/me/context")
            response.raise_for_status()
            data = response.json()
            self._project_id = data["project_id"]
            logger.info(f"Project context loaded: project_id={self._project_id}")

        # At this point, _project_id is guaranteed to be a string (not None)
        assert self._project_id is not None

        return self._project_id

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Internal helper to ensure requests stay scoped to the Dakora API."""
        if path.startswith(("http://", "https://", "//")):
            raise ValueError("path must be a relative Dakora API path")
        headers = kwargs.pop("headers", None)
        if headers is not None:
            sanitized = {k: v for k, v in headers.items() if k.lower() != "x-api-key"}
            if self.__api_key:
                sanitized["X-API-Key"] = self.__api_key
            kwargs["headers"] = sanitized
        return await self.__http.request(method, path, **kwargs)

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Public wrapper for making scoped HTTP requests."""
        return await self._request(method, path, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)

    async def close(self):
        """Close the HTTP client connection (optional - usually not needed)"""
        await self.__http.aclose()

    def update_api_key(self, api_key: str | None) -> None:
        """Update the stored API key and refresh request headers."""
        self.__api_key = api_key
        if api_key:
            self.__http.headers["X-API-Key"] = api_key
        else:
            self.__http.headers.pop("X-API-Key", None)

    def has_api_key(self) -> bool:
        """True if an API key is configured for this client."""
        return self.__api_key is not None

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def project_id(self) -> str | None:
        """
        Get the project ID.

        Automatically fetched from /api/me/context during initialization if API key is present.
        Returns None only if no API key was provided.
        """
        return self._project_id

    def __build_default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.__api_key:
            headers["X-API-Key"] = self.__api_key
        return headers
