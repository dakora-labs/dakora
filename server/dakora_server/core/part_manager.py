"""Part manager for project-scoped prompt parts."""

from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, insert, update, delete, and_, func
from sqlalchemy.engine import Engine

from .database import prompt_parts_table, get_connection
from .exceptions import PartNotFound, ValidationError


class PromptPart:
    """Represents a prompt part."""

    def __init__(
        self,
        id: UUID,
        project_id: UUID,
        part_id: str,
        category: str,
        name: str,
        content: str,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.project_id = project_id
        self.part_id = part_id
        self.category = category
        self.name = name
        self.content = content
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "part_id": self.part_id,
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class PartManager:
    """Manager for project-scoped prompt parts with database operations."""

    def __init__(self, engine: Engine, project_id: UUID):
        """Initialize part manager.

        Args:
            engine: SQLAlchemy engine instance
            project_id: UUID of the project this manager is scoped to
        """
        self.engine = engine
        self.project_id = project_id

    def list_all(self) -> List[PromptPart]:
        """List all parts in the project.

        Returns:
            List of PromptPart objects
        """
        with get_connection(self.engine) as conn:
            stmt = (
                select(prompt_parts_table)
                .where(prompt_parts_table.c.project_id == self.project_id)
                .order_by(prompt_parts_table.c.category, prompt_parts_table.c.name)
            )
            result = conn.execute(stmt)
            rows = result.fetchall()

        return [self._row_to_part(row) for row in rows]

    def list_by_category(self) -> Dict[str, List[PromptPart]]:
        """List all parts grouped by category.

        Returns:
            Dictionary mapping category names to lists of PromptPart objects
        """
        parts = self.list_all()
        by_category: Dict[str, List[PromptPart]] = {}

        for part in parts:
            if part.category not in by_category:
                by_category[part.category] = []
            by_category[part.category].append(part)

        return by_category

    def get(self, part_id: str) -> PromptPart:
        """Get a specific part by ID.

        Args:
            part_id: The part identifier (e.g., "system_role")

        Returns:
            PromptPart object

        Raises:
            PartNotFound: If part doesn't exist in this project
        """
        with get_connection(self.engine) as conn:
            stmt = select(prompt_parts_table).where(
                and_(
                    prompt_parts_table.c.project_id == self.project_id,
                    prompt_parts_table.c.part_id == part_id,
                )
            )
            result = conn.execute(stmt)
            row = result.fetchone()

        if not row:
            raise PartNotFound(f"Prompt part '{part_id}' not found in project")

        return self._row_to_part(row)

    def get_by_category_and_id(self, category: str, part_id: str) -> PromptPart:
        """Get a part by category and ID (for Jinja2 include paths).

        Args:
            category: The category (e.g., "formatting")
            part_id: The part ID (e.g., "json_output")

        Returns:
            PromptPart object

        Raises:
            PartNotFound: If part doesn't exist
        """
        with get_connection(self.engine) as conn:
            stmt = select(prompt_parts_table).where(
                and_(
                    prompt_parts_table.c.project_id == self.project_id,
                    prompt_parts_table.c.category == category,
                    prompt_parts_table.c.part_id == part_id,
                )
            )
            result = conn.execute(stmt)
            row = result.fetchone()

        if not row:
            raise PartNotFound(
                f"Prompt part '{category}/{part_id}' not found in project"
            )

        return self._row_to_part(row)

    def create(
        self,
        part_id: str,
        category: str,
        name: str,
        content: str,
        description: Optional[str] = None,
    ) -> PromptPart:
        """Create a new prompt part.

        Args:
            part_id: Unique identifier for the part (e.g., "system_role")
            category: Category name (e.g., "formatting", "system_roles")
            name: Human-readable name
            content: The actual prompt text
            description: Optional description

        Returns:
            Created PromptPart object

        Raises:
            ValidationError: If part_id already exists in this project
        """
        # Validate part_id format
        if not part_id or not part_id.strip():
            raise ValidationError("part_id cannot be empty")

        # Check for existing part
        try:
            self.get(part_id)
            raise ValidationError(
                f"Part '{part_id}' already exists in this project. "
                f"Use update() to modify existing parts."
            )
        except PartNotFound:
            pass  # Good, part doesn't exist

        with get_connection(self.engine) as conn:
            stmt = (
                insert(prompt_parts_table)
                .values(
                    project_id=self.project_id,
                    part_id=part_id,
                    category=category,
                    name=name,
                    content=content,
                    description=description,
                )
                .returning(prompt_parts_table)
            )
            result = conn.execute(stmt)
            row = result.fetchone()
            conn.commit()

        if not row:
            raise ValidationError("Failed to create prompt part")

        return self._row_to_part(row)

    def update(
        self,
        part_id: str,
        category: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PromptPart:
        """Update an existing prompt part.

        Args:
            part_id: The part identifier
            category: New category (optional)
            name: New name (optional)
            content: New content (optional)
            description: New description (optional)

        Returns:
            Updated PromptPart object

        Raises:
            PartNotFound: If part doesn't exist
        """
        # Verify part exists
        existing = self.get(part_id)

        # Build update values
        values = {"updated_at": func.now()}
        if category is not None:
            values["category"] = category
        if name is not None:
            values["name"] = name
        if content is not None:
            values["content"] = content
        if description is not None:
            values["description"] = description

        with get_connection(self.engine) as conn:
            stmt = (
                update(prompt_parts_table)
                .where(
                    and_(
                        prompt_parts_table.c.project_id == self.project_id,
                        prompt_parts_table.c.part_id == part_id,
                    )
                )
                .values(**values)
                .returning(prompt_parts_table)
            )
            result = conn.execute(stmt)
            row = result.fetchone()
            conn.commit()

        if not row:
            raise PartNotFound(f"Failed to update part '{part_id}'")

        return self._row_to_part(row)

    def delete(self, part_id: str) -> None:
        """Delete a prompt part.

        Args:
            part_id: The part identifier

        Raises:
            PartNotFound: If part doesn't exist
        """
        # Verify part exists
        self.get(part_id)

        with get_connection(self.engine) as conn:
            stmt = delete(prompt_parts_table).where(
                and_(
                    prompt_parts_table.c.project_id == self.project_id,
                    prompt_parts_table.c.part_id == part_id,
                )
            )
            conn.execute(stmt)
            conn.commit()

    def _row_to_part(self, row) -> PromptPart:
        """Convert database row to PromptPart object."""
        return PromptPart(
            id=row.id,
            project_id=row.project_id,
            part_id=row.part_id,
            category=row.category,
            name=row.name,
            content=row.content,
            description=row.description,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
