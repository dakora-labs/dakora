
"""Dakora Platform Client"""

import os
import logging
import httpx

logger = logging.getLogger("dakora_client")


class Dakora:
    """
    Dakora Platform Client

    Create once, reuse everywhere - just like OpenAI's client.

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
        self.api_key = api_key or os.getenv("DAKORA_API_KEY")
        self.base_url = (
            base_url or os.getenv("DAKORA_BASE_URL") or "https://api.dakora.io"
        ).rstrip("/")

        # Mask API key for logging
        masked_key = f"{self.api_key[:8]}..." if self.api_key else None
        logger.debug(
            f"Initializing Dakora client: base_url={self.base_url}, "
            f"api_key={'present' if self.api_key else 'none'}, "
            f"project_id={project_id or 'auto'}"
        )

        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0,
        )

        # Lazy-loaded project context (or explicitly provided)
        self._project_id: str | None = project_id

        # Import here to avoid circular dependency
        from .prompts import PromptsAPI

        self.prompts = PromptsAPI(self)
        logger.info(f"Dakora client initialized for {self.base_url}")

    async def _get_project_id(self) -> str:
        """Get project ID from user context (cached after first call)"""
        if self._project_id is None:
            logger.debug("Fetching project context from /api/me/context")
            response = await self._http.get("/api/me/context")
            response.raise_for_status()
            data = response.json()
            self._project_id = data["project_id"]
            logger.info(f"Project context loaded: project_id={self._project_id}")
        return self._project_id

    async def close(self):
        """Close the HTTP client connection (optional - usually not needed)"""
        await self._http.aclose()