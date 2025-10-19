"""Dakora Platform Client"""

import httpx
from .prompts import PromptsAPI


class Dakora:
    """
    Dakora Platform Client

    Connect to local or cloud Dakora instance.

    Example:
        # Local (Docker)
        dakora = Dakora(url="http://localhost:54321")

        # Cloud
        dakora = Dakora(url="https://api.dakora.cloud", api_key="dk_xxx")
    """

    def __init__(self, url: str, api_key: str | None = None):
        """
        Initialize Dakora client

        Args:
            url: Base URL of the Dakora API server
            api_key: Optional API key for authentication (required for cloud)
        """
        self.url = url.rstrip("/")
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
        """Close the HTTP client"""
        await self._http.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


def create_client(url: str, api_key: str | None = None) -> Dakora:
    """
    Factory function to create Dakora client (Supabase-style)

    Args:
        url: Base URL of the Dakora API server
        api_key: Optional API key for authentication

    Returns:
        Dakora client instance
    """
    return Dakora(url=url, api_key=api_key)