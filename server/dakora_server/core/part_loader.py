"""Jinja2 custom loader for prompt parts from database."""

from typing import Optional, Tuple, Callable
from uuid import UUID

from jinja2 import BaseLoader, TemplateNotFound as Jinja2TemplateNotFound
from sqlalchemy.engine import Engine

from .part_manager import PartManager
from .exceptions import PartNotFound


class PartLoader(BaseLoader):
    """Jinja2 loader that fetches prompt parts from the database.

    This loader enables {% include "category/part_id" %} syntax in templates,
    where parts are fetched from the project-scoped prompt_parts table.

    Example:
        {% include "formatting/json_output" %}
        {% include "system_roles/system_role" %}
    """

    def __init__(self, engine: Engine, project_id: UUID):
        """Initialize the part loader.

        Args:
            engine: SQLAlchemy engine instance
            project_id: UUID of the project to load parts from
        """
        self.engine = engine
        self.project_id = project_id
        self._manager: Optional[PartManager] = None

    @property
    def manager(self) -> PartManager:
        """Lazy-load part manager."""
        if self._manager is None:
            self._manager = PartManager(self.engine, self.project_id)
        return self._manager

    def get_source(
        self, environment, template: str
    ) -> Tuple[str, Optional[str], Callable[[], bool]]:
        """Load a prompt part by its path.

        Args:
            environment: Jinja2 environment (unused)
            template: Template path in format "category/part_id"

        Returns:
            Tuple of (source, filename, uptodate_func)
            - source: The part content
            - filename: None (parts don't have filenames)
            - uptodate_func: Always returns True (no file modification checking)

        Raises:
            Jinja2TemplateNotFound: If the part doesn't exist
        """
        # Parse template path: "formatting/json_output" -> ("formatting", "json_output")
        try:
            category, part_id = template.split("/", 1)
        except ValueError:
            raise Jinja2TemplateNotFound(
                f"Invalid part path '{template}'. Expected format: 'category/part_id'"
            )

        # Fetch part from database
        try:
            part = self.manager.get_by_category_and_id(category, part_id)
        except PartNotFound:
            raise Jinja2TemplateNotFound(
                f"Prompt part '{template}' not found in project"
            )

        # Return (source, filename, uptodate_func)
        # uptodate_func returns True = always consider fresh (no file modification checking)
        return part.content, None, lambda: True

    def list_templates(self) -> list[str]:
        """List all available template paths.

        Returns:
            List of template paths in format "category/part_id"
        """
        parts = self.manager.list_all()
        return [f"{part.category}/{part.part_id}" for part in parts]