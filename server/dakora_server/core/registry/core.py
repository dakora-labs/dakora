"""Core template registry implementation."""
from __future__ import annotations
from pathlib import PurePosixPath
from typing import Iterable, Optional
import warnings
import yaml
from .base import Registry
from .backends import StorageBackend
from .serialization import parse_yaml, render_yaml
from ..model import TemplateSpec
from ..exceptions import TemplateNotFound, RegistryError, ValidationError

__all__ = ["TemplateRegistry"]


class TemplateRegistry(Registry):
    """Core template registry implementation with pluggable storage backends.

    This registry works with any storage backend implementing the StorageBackend
    protocol, enabling template storage in local filesystems, cloud storage, or
    other custom backends.

    Naming convention: Templates are stored as {id}.yaml files. For backward
    compatibility, the load() method will scan all YAML files if direct lookup fails.
    """

    def __init__(self, backend: StorageBackend, *, prefix: str | None = None) -> None:
        """Initialize registry with a storage backend.

        Args:
            backend: Storage backend implementing StorageBackend protocol
            prefix: Optional path prefix to scope registry operations
        """
        self.backend = backend
        self._prefix = self._normalize_prefix(prefix)

    @staticmethod
    def _normalize_prefix(prefix: str | None) -> str:
        if not prefix:
            return ""
        candidate = PurePosixPath(prefix.strip())
        parts: list[str] = []
        for part in candidate.parts:
            if part in {"", "."}:
                continue
            if part == "..":
                raise ValueError("Registry prefix cannot contain '..'")
            parts.append(part)
        return "/".join(parts)

    def _full_name(self, name: str) -> str:
        clean = name.lstrip("/")
        if not self._prefix:
            return clean
        return f"{self._prefix}/{clean}"

    def _iter_scoped_entries(self) -> Iterable[tuple[str, str]]:
        if not self._prefix:
            for entry in self.backend.list():
                yield entry, entry
            return

        prefix_with_sep = f"{self._prefix}/"
        for entry in self.backend.list():
            if entry == self._prefix:
                continue
            if entry.startswith(prefix_with_sep):
                yield entry, entry[len(prefix_with_sep) :]

    def with_prefix(self, extra_prefix: str | None) -> "TemplateRegistry":
        """Return a scoped registry rooted at an additional prefix."""
        combined = self._combine_prefix(extra_prefix)
        if combined == self._prefix:
            return self
        return TemplateRegistry(self.backend, prefix=combined)

    def _combine_prefix(self, extra_prefix: str | None) -> str:
        extra = self._normalize_prefix(extra_prefix)
        if not extra:
            return self._prefix
        if not self._prefix:
            return extra
        return f"{self._prefix}/{extra}"

    # --- Internal helpers ----------------------------------------------
    def _load_and_normalize(
        self,
        name: str,
        expected_id: Optional[str] = None,
    ) -> Optional[TemplateSpec]:
        """Load template from file and normalize.

        Args:
            name: File name to load
            expected_id: If provided, only return spec if ID matches

        Returns:
            TemplateSpec if successfully loaded (and ID matches if expected_id given),
            None otherwise
        """
        try:
            data = parse_yaml(self.backend.read_text(name))

            # YAML files that define `template:` with no value are parsed as
            # None by yaml.safe_load. TemplateSpec requires `template` to be a
            # string; coerce explicit null to empty string so these files are
            # treated as empty templates instead of failing validation.
            if "template" in data and data.get("template") is None:
                data["template"] = ""

            # If we expect a specific ID, verify it matches
            if expected_id is not None and data.get("id") != expected_id:
                return None

            spec = TemplateSpec.model_validate(data)

            # Normalize: strip trailing newlines added by YAML block scalar format
            # This ensures templates are stored consistently regardless of YAML serialization
            if spec.template.endswith("\n"):
                spec.template = spec.template.rstrip("\n")

            return spec
        except yaml.YAMLError as e:
            warnings.warn(f"YAML parse error in {name}: {e}", stacklevel=2)
            return None
        except ValidationError as e:
            warnings.warn(f"Template validation error in {name}: {e}", stacklevel=2)
            return None
        except Exception as e:
            # Unexpected errors - log but don't crash
            warnings.warn(f"Unexpected error loading {name}: {e}", stacklevel=2)
            return None

    # --- Registry API --------------------------------------------------
    def list_ids(self) -> Iterable[str]:  # type: ignore[override]
        """List all template IDs in the registry.

        Uses filename-based convention for performance (assumes files are named {id}.yaml).
        This is especially important for cloud storage backends where each read is a network call.

        The save() method enforces this naming convention, so this is safe for new templates.

        Returns:
            Iterable of template IDs
        """
        seen: set[str] = set()
        for _full_name, relative_name in self._iter_scoped_entries():
            if not relative_name.endswith((".yaml", ".yml")):
                continue
            # Extract ID from filename (matches save convention: {spec.id}.yaml)
            stem = relative_name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if stem and stem not in seen:
                seen.add(stem)
                yield stem

    def load(self, template_id: str) -> TemplateSpec:  # type: ignore[override]
        """Load a template by ID.

        First attempts direct lookup using naming convention ({id}.yaml or {id}.yml).
        Falls back to scanning all files if direct lookup fails or ID mismatches.

        Args:
            template_id: The template ID to load

        Returns:
            TemplateSpec for the requested template

        Raises:
            TemplateNotFound: If no template with given ID exists
        """
        # Try direct lookup first (fast path)
        candidates = [f"{template_id}.yaml", f"{template_id}.yml"]
        for candidate in candidates:
            full_candidate = self._full_name(candidate)
            if self.backend.exists(full_candidate):
                spec = self._load_and_normalize(full_candidate, expected_id=template_id)
                if spec is not None:
                    return spec

        # Fallback: scan all files (slow path for backwards compatibility)
        for full_name, relative_name in self._iter_scoped_entries():
            if not relative_name.endswith((".yaml", ".yml")):
                continue
            spec = self._load_and_normalize(full_name, expected_id=template_id)
            if spec is not None:
                return spec

        raise TemplateNotFound(template_id)

    def save(self, spec: TemplateSpec) -> None:  # type: ignore[override]
        """Save a template to storage.

        Templates are saved using the naming convention {id}.yaml, which enables
        efficient direct lookups without scanning all files.

        Args:
            spec: Template specification to save

        Raises:
            RegistryError: If save operation fails
        """
        filename = f"{spec.id}.yaml"
        full_name = self._full_name(filename)
        original = self.backend.read_text(full_name) if self.backend.exists(full_name) else None
        try:
            text = render_yaml(spec, original)
            self.backend.write_text(full_name, text)
        except Exception as e:  # pragma: no cover
            raise RegistryError(f"Failed to save template '{spec.id}': {e}") from e

    def delete(self, template_id: str) -> None:  # type: ignore[override]
        """Delete a template from storage.

        First attempts direct lookup using naming convention ({id}.yaml or {id}.yml).
        Falls back to scanning all files if direct lookup fails.

        Args:
            template_id: The template ID to delete

        Raises:
            TemplateNotFound: If template doesn't exist
            RegistryError: If deletion fails
        """
        # Try direct lookup first (fast path)
        candidates = [f"{template_id}.yaml", f"{template_id}.yml"]
        deleted = False

        for candidate in candidates:
            full_candidate = self._full_name(candidate)
            if self.backend.exists(full_candidate):
                try:
                    self.backend.delete(full_candidate)
                    deleted = True
                    break
                except Exception as e:
                    raise RegistryError(f"Failed to delete template '{template_id}': {e}") from e

        if not deleted:
            # Fallback: scan all files to find the template (slow path for backwards compatibility)
            for full_name, relative_name in self._iter_scoped_entries():
                if not relative_name.endswith((".yaml", ".yml")):
                    continue
                # Check if this file contains the template we want to delete
                spec = self._load_and_normalize(full_name, expected_id=template_id)
                if spec is not None:
                    try:
                        self.backend.delete(full_name)
                        deleted = True
                        break
                    except Exception as e:
                        raise RegistryError(f"Failed to delete template '{template_id}': {e}") from e

        if not deleted:
            raise TemplateNotFound(template_id)
