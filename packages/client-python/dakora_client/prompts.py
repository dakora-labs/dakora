"""Prompts API client"""

import logging
from typing import TYPE_CHECKING, Any

from .types import RenderResult

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
        project_id = await self._client._get_project_id() # type: ignore
        url = f"/api/projects/{project_id}/prompts"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        templates = response.json()
        logger.info(f"Listed {len(templates)} prompts")
        return templates

    async def render(
        self,
        template_id: str,
        inputs: dict[str, Any],
        version: str | None = None,
        embed_metadata: bool = True
    ) -> RenderResult:
        """Render a prompt template with inputs and return execution context.

        Template tracking is enabled by default via embedded metadata markers.
        This allows linking executions to templates across any agent framework.

        Args:
            template_id: ID of the template to render
            inputs: Variables to substitute in the template
            version: Specific version to render (optional, defaults to latest)
            embed_metadata: Embed tracking metadata in rendered text (default: True).
                Set to False to disable tracking and reduce token overhead.

        Returns:
            RenderResult with rendered text and metadata for template tracking

        Example:
            # Default: tracking enabled
            result = await client.prompts.render(
                "greeting",
                {"name": "Alice", "role": "Developer"}
            )
            # Text includes: <!--dakora:prompt_id=greeting,version=1.0.0-->

            # Opt-out of tracking
            result = await client.prompts.render(
                "greeting",
                {"name": "Alice"},
                embed_metadata=False
            )
            # Text has no tracking metadata
        """
        project_id = await self._client._get_project_id() # type: ignore
        url = f"/api/projects/{project_id}/prompts/{template_id}/render"

        payload: dict[str, Any] = {"inputs": inputs}
        if version:
            payload["version"] = version

        logger.debug(f"POST {url} with {len(inputs)} inputs")
        response = await self._client.post(url, json=payload)
        logger.debug(f"POST {url} -> {response.status_code}")

        response.raise_for_status()
        data = response.json()

        rendered_text = data["rendered"]
        template_version = data.get("version", version or "latest")

        # Optionally embed metadata in text for tracking
        if embed_metadata:
            metadata_marker = f"<!--dakora:prompt_id={template_id},version={template_version}-->\n"
            rendered_text = metadata_marker + rendered_text
            logger.debug(f"Embedded tracking metadata for '{template_id}' v{template_version}")

        result = RenderResult(
            text=rendered_text,
            prompt_id=template_id,
            version=template_version,
            inputs=inputs,
            metadata={},
        )

        logger.info(f"Rendered prompt '{template_id}' v{result.version} ({len(result.text)} chars)")
        return result

    async def create(
        self,
        prompt_id: str,
        template: str,
        version: str = "1.0.0",
        description: str | None = None,
        inputs: dict[str, dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new prompt template.

        Args:
            prompt_id: Unique identifier for the prompt
            template: The prompt template text (supports Jinja2 syntax)
            version: Semantic version (default: "1.0.0")
            description: Human-readable description (optional)
            inputs: Input schema definition (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created prompt data

        Example:
            await client.prompts.create(
                prompt_id="greeting",
                template="Hello {{name}}!",
                description="Simple greeting template",
                inputs={
                    "name": {"type": "string", "required": True}
                },
                metadata={"category": "greetings"}
            )
        """
        project_id = await self._client._get_project_id()  # type: ignore
        url = f"/api/projects/{project_id}/prompts"

        payload = {
            "id": prompt_id,
            "version": version,
            "template": template,
            "description": description,
            "inputs": inputs or {},
            "metadata": metadata or {},
        }

        logger.debug(f"POST {url} - creating prompt '{prompt_id}'")
        response = await self._client.post(url, json=payload)
        logger.debug(f"POST {url} -> {response.status_code}")

        response.raise_for_status()
        data = response.json()
        logger.info(f"Created prompt '{prompt_id}' v{version}")
        return data

    async def get(self, prompt_id: str) -> dict[str, Any]:
        """Get a prompt template by ID.

        Args:
            prompt_id: ID of the prompt to retrieve

        Returns:
            Prompt template data

        Example:
            prompt = await client.prompts.get("greeting")
            print(prompt["template"])
        """
        project_id = await self._client._get_project_id()  # type: ignore
        url = f"/api/projects/{project_id}/prompts/{prompt_id}"

        logger.debug(f"GET {url}")
        response = await self._client.get(url)
        logger.debug(f"GET {url} -> {response.status_code}")

        response.raise_for_status()
        data = response.json()
        logger.info(f"Retrieved prompt '{prompt_id}'")
        return data
