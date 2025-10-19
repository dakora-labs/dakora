"""Prompts API client"""

from typing import List, Dict, Any
import httpx
from .types import TemplateInfo, RenderResult, CompareResult


class PromptsAPI:
    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def list(self) -> List[str]:
        """List all available template IDs"""
        response = await self._http.get("/api/templates")
        response.raise_for_status()
        return response.json()

    async def get(self, template_id: str) -> TemplateInfo:
        """Get a specific template with all its details"""
        response = await self._http.get(f"/api/templates/{template_id}")
        response.raise_for_status()
        return TemplateInfo(**response.json())

    async def create(
        self,
        id: str,
        template: str,
        version: str = "1.0.0",
        description: str | None = None,
        inputs: Dict[str, Dict[str, Any]] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> TemplateInfo:
        """Create a new template"""
        payload = {
            "id": id,
            "version": version,
            "template": template,
            "description": description,
            "inputs": inputs or {},
            "metadata": metadata or {},
        }
        response = await self._http.post("/api/templates", json=payload)
        response.raise_for_status()
        return TemplateInfo(**response.json())

    async def update(
        self,
        template_id: str,
        version: str | None = None,
        description: str | None = None,
        template: str | None = None,
        inputs: Dict[str, Dict[str, Any]] | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> TemplateInfo:
        """Update an existing template"""
        payload = {}
        if version is not None:
            payload["version"] = version
        if description is not None:
            payload["description"] = description
        if template is not None:
            payload["template"] = template
        if inputs is not None:
            payload["inputs"] = inputs
        if metadata is not None:
            payload["metadata"] = metadata

        response = await self._http.put(f"/api/templates/{template_id}", json=payload)
        response.raise_for_status()
        return TemplateInfo(**response.json())

    async def render(
        self, template_id: str, inputs: Dict[str, Any] | None = None
    ) -> RenderResult:
        """Render a template with provided inputs"""
        payload = {"inputs": inputs or {}}
        response = await self._http.post(
            f"/api/templates/{template_id}/render", json=payload
        )
        response.raise_for_status()
        return RenderResult(**response.json())

    async def compare(
        self,
        template_id: str,
        models: List[str],
        inputs: Dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
        **params,
    ) -> CompareResult:
        """Compare template execution across multiple LLM models"""
        payload = {
            "models": models,
            "inputs": inputs or {},
            "params": params,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p

        response = await self._http.post(
            f"/api/templates/{template_id}/compare", json=payload
        )
        response.raise_for_status()
        return CompareResult(**response.json())