"""Prompt management layer that syncs between blob storage and database."""

from __future__ import annotations
import hashlib
import yaml
from datetime import datetime
from uuid import UUID
from typing import Iterable, Optional
from sqlalchemy.engine import Engine
from sqlalchemy import select, insert, update, delete

from .model import TemplateSpec
from .registry import Registry
from .registry.serialization import render_yaml
from .database import prompts_table, prompt_versions_table, get_connection
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

    def _calculate_content_hash(self, spec: TemplateSpec) -> str:
        """Calculate SHA256 hash of normalized YAML content.

        Normalizes the YAML by parsing and re-serializing with consistent
        formatting to avoid false positives from superficial changes.

        Args:
            spec: Template specification to hash

        Returns:
            Hex-encoded SHA256 hash
        """
        # Render YAML content with consistent formatting
        yaml_content = render_yaml(spec, original_text=None)

        # Parse and re-serialize to normalize formatting
        parsed = yaml.safe_load(yaml_content)
        normalized = yaml.dump(parsed, sort_keys=True, default_flow_style=False)

        # Calculate hash
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

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

            # If project exists in DB, load from versioned storage path
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

                storage_path = result[1]

                # Load from versioned storage path
                from .registry.serialization import parse_yaml
                yaml_content = self.registry.backend.read_text(storage_path)
                data = parse_yaml(yaml_content)

                # Handle null template
                if "template" in data and data.get("template") is None:
                    data["template"] = ""

                return TemplateSpec.model_validate(data)

        # No-auth mode: load from blob storage via registry
        return self.registry.load(prompt_id)

    def save(self, spec: TemplateSpec, user_id: Optional[UUID] = None) -> None:
        """Save a prompt with automatic versioning.

        Creates a new version if content has changed. If content is identical
        to the current version, this is a no-op (idempotent saves).

        Args:
            spec: Template specification to save
            user_id: User ID for version tracking (optional)

        Raises:
            RegistryError: If save operation fails
        """
        # Calculate content hash for change detection
        new_content_hash = self._calculate_content_hash(spec)

        # Check if project exists (skip versioning in no-auth mode)
        with get_connection(self.engine) as conn:
            from .database import projects_table
            project_exists = conn.execute(
                select(projects_table.c.id)
                .where(projects_table.c.id == self.project_id)
            ).fetchone()

            if not project_exists:
                # No-auth mode: just save to registry without versioning
                self.registry.save(spec)
                return

            # Check if prompt already exists
            existing = conn.execute(
                select(
                    prompts_table.c.id,
                    prompts_table.c.version_number,
                    prompts_table.c.content_hash,
                    prompts_table.c.storage_path
                )
                .where(
                    prompts_table.c.project_id == self.project_id,
                    prompts_table.c.prompt_id == spec.id,
                )
            ).fetchone()

            if existing:
                db_id, current_version, current_hash, current_storage = existing

                # Check if content has changed
                if current_hash == new_content_hash:
                    # Content unchanged - no-op for idempotent saves
                    return

                # Content changed - create new version
                new_version = current_version + 1

                # Migrate existing file to v1 if needed
                if current_storage == f"projects/{self.project_id}/{spec.id}.yaml":
                    self._migrate_to_v1(spec.id, current_version, current_hash, user_id)

                # Save new version to storage
                version_path = f"projects/{self.project_id}/{spec.id}_v{new_version}.yaml"
                self._save_versioned_file(spec, version_path)

                # Update prompts table
                conn.execute(
                    update(prompts_table)
                    .where(prompts_table.c.id == db_id)
                    .values(
                        version_number=new_version,
                        content_hash=new_content_hash,
                        version=spec.version,
                        description=spec.description,
                        storage_path=version_path,
                        last_updated_at=datetime.utcnow(),
                        metadata=spec.metadata or {},
                    )
                )

                # Create version history entry
                conn.execute(
                    insert(prompt_versions_table).values(
                        prompt_id=db_id,
                        version_number=new_version,
                        content_hash=new_content_hash,
                        created_by=user_id,
                        storage_path=version_path,
                        metadata=spec.metadata or {},
                    )
                )

            else:
                # New prompt - create with version 1
                storage_path = f"projects/{self.project_id}/{spec.id}_v1.yaml"
                self._save_versioned_file(spec, storage_path)

                # Insert into prompts table
                result = conn.execute(
                    insert(prompts_table).values(
                        project_id=self.project_id,
                        prompt_id=spec.id,
                        version_number=1,
                        content_hash=new_content_hash,
                        version=spec.version,
                        description=spec.description,
                        storage_path=storage_path,
                        metadata=spec.metadata or {},
                    ).returning(prompts_table.c.id)
                )
                db_id = result.fetchone()[0]

                # Create initial version history entry
                conn.execute(
                    insert(prompt_versions_table).values(
                        prompt_id=db_id,
                        version_number=1,
                        content_hash=new_content_hash,
                        created_by=user_id,
                        storage_path=storage_path,
                        metadata=spec.metadata or {},
                    )
                )

            conn.commit()

    def _save_versioned_file(self, spec: TemplateSpec, storage_path: str) -> None:
        """Save a versioned YAML file directly to storage backend.

        Args:
            spec: Template specification to save
            storage_path: Full storage path including version suffix
        """
        yaml_content = render_yaml(spec, original_text=None)
        self.registry.backend.write_text(storage_path, yaml_content)

    def _migrate_to_v1(self, prompt_id: str, version: int, content_hash: Optional[str], user_id: Optional[UUID]) -> None:
        """Migrate existing prompt file without version suffix to v{version}.yaml.

        Args:
            prompt_id: The prompt ID
            version: Current version number
            content_hash: Content hash of current version (will be calculated if None)
            user_id: User ID for version tracking (optional)
        """
        # Read existing file
        old_path = f"projects/{self.project_id}/{prompt_id}.yaml"
        new_path = f"projects/{self.project_id}/{prompt_id}_v{version}.yaml"

        try:
            # Copy content to versioned path
            content = self.registry.backend.read_text(old_path)
            self.registry.backend.write_text(new_path, content)

            # Calculate content hash if not provided (for pre-migration prompts)
            if content_hash is None:
                import yaml
                data = yaml.safe_load(content)
                spec = TemplateSpec.model_validate(data)
                content_hash = self._calculate_content_hash(spec)

            # Create version history entry for the migrated version
            with get_connection(self.engine) as conn:
                db_id_result = conn.execute(
                    select(prompts_table.c.id)
                    .where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                ).fetchone()

                if db_id_result:
                    db_id = db_id_result[0]
                    # Check if version entry already exists
                    existing_version = conn.execute(
                        select(prompt_versions_table.c.id)
                        .where(
                            prompt_versions_table.c.prompt_id == db_id,
                            prompt_versions_table.c.version_number == version,
                        )
                    ).fetchone()

                    if not existing_version:
                        conn.execute(
                            insert(prompt_versions_table).values(
                                prompt_id=db_id,
                                version_number=version,
                                content_hash=content_hash,
                                created_by=user_id,
                                storage_path=new_path,
                                metadata={},
                            )
                        )
                        conn.commit()

            # Delete old file (optional - could keep for backup)
            # self.registry.backend.delete(old_path)
        except Exception as e:
            # Log error but don't fail the save operation
            import logging
            logging.getLogger(__name__).warning(
                f"Failed to migrate {prompt_id} to versioned path: {e}"
            )

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

            # If project exists in DB, get all version files to delete
            if project_exists:
                # Get prompt info including all versions
                prompt_result = conn.execute(
                    select(prompts_table.c.id, prompts_table.c.storage_path)
                    .where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                ).fetchone()

                if not prompt_result:
                    raise TemplateNotFound(prompt_id)

                db_id, current_storage_path = prompt_result

                # Get all version storage paths
                version_results = conn.execute(
                    select(prompt_versions_table.c.storage_path)
                    .where(prompt_versions_table.c.prompt_id == db_id)
                ).fetchall()

                # Delete all version files from storage
                storage_paths = {current_storage_path} | {row[0] for row in version_results}
                for storage_path in storage_paths:
                    try:
                        self.registry.backend.delete(storage_path)
                    except Exception as e:
                        # Log warning but continue deleting other files
                        import logging
                        logging.getLogger(__name__).warning(
                            f"Failed to delete {storage_path}: {e}"
                        )

                # Delete from database
                conn.execute(
                    delete(prompts_table).where(
                        prompts_table.c.project_id == self.project_id,
                        prompts_table.c.prompt_id == prompt_id,
                    )
                )
                conn.commit()
            else:
                # No-auth mode: delete via registry (non-versioned file)
                self.registry.delete(prompt_id)

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

    def get_version_history(self, prompt_id: str) -> list[dict]:
        """Get version history for a prompt.

        Args:
            prompt_id: The prompt ID

        Returns:
            List of version records with metadata, ordered newest first

        Raises:
            TemplateNotFound: If prompt doesn't exist
        """
        with get_connection(self.engine) as conn:
            # Get prompt database ID
            prompt_result = conn.execute(
                select(prompts_table.c.id)
                .where(
                    prompts_table.c.project_id == self.project_id,
                    prompts_table.c.prompt_id == prompt_id,
                )
            ).fetchone()

            if not prompt_result:
                raise TemplateNotFound(prompt_id)

            prompt_db_id = prompt_result[0]

            # Get all versions
            result = conn.execute(
                select(
                    prompt_versions_table.c.version_number,
                    prompt_versions_table.c.content_hash,
                    prompt_versions_table.c.created_at,
                    prompt_versions_table.c.created_by,
                    prompt_versions_table.c.storage_path,
                    prompt_versions_table.c.metadata,
                )
                .where(prompt_versions_table.c.prompt_id == prompt_db_id)
                .order_by(prompt_versions_table.c.version_number.desc())
            )

            versions = []
            for row in result.fetchall():
                versions.append({
                    "version": row[0],
                    "content_hash": row[1],
                    "created_at": row[2],
                    "created_by": row[3],
                    "storage_path": row[4],
                    "metadata": row[5] or {},
                })

            return versions

    def get_version_content(self, prompt_id: str, version: int) -> TemplateSpec:
        """Load a specific version of a prompt.

        Args:
            prompt_id: The prompt ID
            version: Version number to load

        Returns:
            TemplateSpec for the requested version

        Raises:
            TemplateNotFound: If prompt or version doesn't exist
        """
        with get_connection(self.engine) as conn:
            # Get prompt database ID
            prompt_result = conn.execute(
                select(prompts_table.c.id)
                .where(
                    prompts_table.c.project_id == self.project_id,
                    prompts_table.c.prompt_id == prompt_id,
                )
            ).fetchone()

            if not prompt_result:
                raise TemplateNotFound(prompt_id)

            prompt_db_id = prompt_result[0]

            # Get version storage path
            version_result = conn.execute(
                select(prompt_versions_table.c.storage_path)
                .where(
                    prompt_versions_table.c.prompt_id == prompt_db_id,
                    prompt_versions_table.c.version_number == version,
                )
            ).fetchone()

            if not version_result:
                raise TemplateNotFound(f"{prompt_id} (version {version})")

            storage_path = version_result[0]

            # Load from storage backend
            from .registry.serialization import parse_yaml
            yaml_content = self.registry.backend.read_text(storage_path)
            data = parse_yaml(yaml_content)

            # Handle null template
            if "template" in data and data.get("template") is None:
                data["template"] = ""

            return TemplateSpec.model_validate(data)

    def rollback_to_version(self, prompt_id: str, target_version: int, user_id: Optional[UUID] = None) -> TemplateSpec:
        """Rollback to a previous version by creating a new version with old content.

        This creates a new version (e.g., v5) with the content from target_version,
        rather than actually reverting the version number. This preserves full
        history and makes rollbacks auditable.

        Args:
            prompt_id: The prompt ID
            target_version: Version number to rollback to
            user_id: User ID for version tracking (optional)

        Returns:
            New TemplateSpec with incremented version

        Raises:
            TemplateNotFound: If prompt or target version doesn't exist
        """
        # Load the target version content
        target_spec = self.get_version_content(prompt_id, target_version)

        # Save as new version (this will auto-increment)
        self.save(target_spec, user_id=user_id)

        # Return the newly saved spec
        return self.load(prompt_id)