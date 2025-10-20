"""Dakora Platform Client"""

import httpx
from .prompts import PromptsAPI


class Dakora:
    """
    Dakora Platform Client

    Connect to local or cloud Dakora instance.

    Example:
        # Local (Docker)
        from dakora_client import Dakora

        dakora = Dakora("http://localhost:54321")
        templates = await dakora.prompts.list()

        # Cloud
        dakora = Dakora("https://api.dakora.cloud", api_key="dk_xxx")
        result = await dakora.prompts.render("greeting", {"name": "Alice"})
    """

    def __init__(self, url: str, api_key: str | None = None):
        """
        Initialize Dakora client

        Args:
            url: Base URL of the Dakora API server
            api_key: Optional API key for authentication (required for cloud)
        """
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._http = httpx.AsyncClient(
            base_url=self.url,
            headers={"apikey": api_key} if api_key else {},
            timeout=30.0,
        )

        self.prompts = PromptsAPI(self._http)

    async def health(self) -> dict:
        """Check server health status"""
        response = await self._http.get("/api/health")
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client connection"""
        await self._http.aclose()