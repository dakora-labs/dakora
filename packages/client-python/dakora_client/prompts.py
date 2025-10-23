"""Prompts API client"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import Dakora

logger = logging.getLogger("dakora_client.prompts")


class PromptsAPI:
    """Prompts API client"""

    def __init__(self, client: "Dakora"):
        self._client = client

    async def list(self) -> list[str]:
        """List all prompt template IDs.

        Returns:
            List of prompt IDs

        Example:
            templates = await client.prompts.list()
            # ["greeting", "email", "summary"]
        """
        project_id = await self._client._get_project_id()
        url = f"/api/projects/{project_id}/prompts"

        logger.debug(f"GET {url}")
        response = await self._client._http.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        templates = response.json()
        logger.info(f"Listed {len(templates)} prompts")
        return templates

    async def render(self, template_id: str, inputs: dict[str, Any]) -> str:
        """Render a prompt template with inputs.

        Args:
            template_id: ID of the template to render
            inputs: Variables to substitute in the template

        Returns:
            Rendered template text

        Example:
            result = await client.prompts.render(
                "greeting",
                {"name": "Alice", "role": "Developer"}
            )
        """
        project_id = await self._client._get_project_id()
        url = f"/api/projects/{project_id}/prompts/{template_id}/render"

        logger.debug(f"POST {url} with {len(inputs)} inputs")
        response = await self._client._http.post(
            url,
            json={"inputs": inputs},
        )
        logger.debug(f"POST {url} -> {response.status_code}")

        response.raise_for_status()
        data = response.json()
        rendered = data["rendered"]
        logger.info(f"Rendered prompt '{template_id}' ({len(rendered)} chars)")
        return rendered