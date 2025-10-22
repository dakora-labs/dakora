"""Prompt management layer that syncs between blob storage and database."""

from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import Iterable, Optional
from sqlalchemy.engine import Engine
from sqlalchemy import select, insert, update, delete

from .model import TemplateSpec
from .registry import Registry
from .database import prompts_table, get_connection
from .exceptions import TemplateNotFound, RegistryError


class PromptManager:
    """Manages prompts with database indexing and blob storage.

    This layer sits on top of the Registry and ensures that:
    1. All prompt metadata is tracked in the database
    2. Actual YAML content is stored in blob storage via Registry
    3. Changes are synced between both storage layers
    """

    def __init__(self, registry: Registry, engine: Engine, project_id: UUID):
        """Initialize prompt manager.

        Args:
            registry: Registry for blob storage operations
            engine: Database engine for metadata operations
            project_id: Project UUID this manager is scoped to
        """
        self.registry = registry
        self.engine = engine
        self.project_id = project_id

    def list_ids(self) -> list[str]:
        """List all prompt IDs for this project from database.
        
        In no-auth mode (when project doesn't exist in DB), falls back to registry.

        Returns:
            List of prompt IDs
        """
        with get_connection(self.engine) as conn:
            # Check if project exists in database
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()
            
            # If project doesn't exist, use registry directly (no-auth mode)
            if not project_exists:
                return list(self.registry.list_ids())
            
            # Otherwise, use database for listing
            result = conn.execute(
                select(prompts_table.c.prompt_id)
                .where(prompts_table.c.project_id == self.project_id)
                .order_by(prompts_table.c.last_updated_at.desc())
            )
            return [row[0] for row in result.fetchall()]

    def load(self, prompt_id: str) -> TemplateSpec:
        """Load a prompt by ID.

        Args:
            prompt_id: The prompt ID to load

        Returns:
            TemplateSpec from blob storage

        Raises:
            TemplateNotFound: If prompt not found in database or storage
        """
        # Check if project exists in database
        with get_connection(self.engine) as conn:
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()
            
            # If project exists in DB, verify prompt exists in database first
            if project_exists:
                result = conn.execute(
                    select(prompts_table.c.id, prompts_table.c.storage_path)
                    .where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                ).fetchone()

                if not result:
                    raise TemplateNotFound(prompt_id)

        # Load from blob storage via registry (works in both auth and no-auth modes)
        return self.registry.load(prompt_id)

    def save(self, spec: TemplateSpec) -> None:
        """Save a prompt to both blob storage and database.

        Args:
            spec: Template specification to save

        Raises:
            RegistryError: If save operation fails
        """
        # Save to blob storage first
        self.registry.save(spec)

        # Compute storage path (matches registry naming convention)
        storage_path = f"projects/{self.project_id}/{spec.id}.yaml"

        # Sync to database (skip if project doesn't exist - e.g., no-auth mode)
        with get_connection(self.engine) as conn:
            # Check if project exists in database
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()
            
            # Skip database sync if project doesn't exist (no-auth mode)
            if not project_exists:
                return
            
            # Check if record exists
            existing = conn.execute(
                select(prompts_table.c.id)
                .where(
                    prompts_table.c.project_id == self.project_id,
                    prompts_table.c.prompt_id == spec.id,
                )
            ).fetchone()

            if existing:
                # Update existing record
                conn.execute(
                    update(prompts_table)
                    .where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == spec.id,
                    )
                    .values(
                        version=spec.version,
                        description=spec.description,
                        storage_path=storage_path,
                        last_updated_at=datetime.utcnow(),
                        metadata=spec.metadata or {},
                    )
                )
            else:
                # Insert new record
                conn.execute(
                    insert(prompts_table).values(
                        project_id=self.project_id,
                        prompt_id=spec.id,
                        version=spec.version,
                        description=spec.description,
                        storage_path=storage_path,
                        metadata=spec.metadata or {},
                    )
                )

            conn.commit()

    def delete(self, prompt_id: str) -> None:
        """Delete a prompt from both blob storage and database.

        Args:
            prompt_id: The prompt ID to delete

        Raises:
            TemplateNotFound: If prompt doesn't exist
            RegistryError: If deletion fails
        """
        # Check database first (skip if project doesn't exist - no-auth mode)
        with get_connection(self.engine) as conn:
            # Check if project exists in database
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()
            
            # If project exists in DB, verify prompt exists
            if project_exists:
                existing = conn.execute(
                    select(prompts_table.c.id)
                    .where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                ).fetchone()

                if not existing:
                    raise TemplateNotFound(prompt_id)

        # Delete from blob storage
        self.registry.delete(prompt_id)

        # Delete from database (skip if project doesn't exist - no-auth mode)
        with get_connection(self.engine) as conn:
            # Check if project exists
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()
            
            if project_exists:
                conn.execute(
                    delete(prompts_table).where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                )
            conn.commit()

    def sync_from_storage(self) -> int:
        """Sync database records from blob storage.

        Scans all prompts in blob storage and ensures they're tracked in database.
        Useful for initial migration or recovering from database loss.

        Returns:
            Number of prompts synced
        """
        synced = 0

        # Get all prompt IDs from registry
        storage_ids = set(self.registry.list_ids())

        # Get all prompt IDs from database
        with get_connection(self.engine) as conn:
            result = conn.execute(
                select(prompts_table.c.prompt_id).where(
                    prompts_table.c.project_id == self.project_id
                )
            )
            db_ids = {row[0] for row in result.fetchall()}

        # Find prompts in storage but not in database
        missing_ids = storage_ids - db_ids

        for prompt_id in missing_ids:
            try:
                spec = self.registry.load(prompt_id)
                storage_path = f"projects/{self.project_id}/{spec.id}.yaml"

                with get_connection(self.engine) as conn:
                    conn.execute(
                        insert(prompts_table).values(
                            project_id=self.project_id,
                            prompt_id=spec.id,
                            version=spec.version,
                            description=spec.description,
                            storage_path=storage_path,
                            metadata=spec.metadata or {},
                        )
                    )
                    conn.commit()

                synced += 1
            except Exception:
                # Skip prompts that fail to load
                continue

        return synced