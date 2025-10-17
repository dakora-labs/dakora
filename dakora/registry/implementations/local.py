"""Local filesystem template registry implementation."""
from __future__ import annotations
from typing import Iterable
from pathlib import Path
from ..core import TemplateRegistry
from ..backends import LocalFSBackend
from ...model import TemplateSpec

__all__ = ["LocalRegistry"]


class LocalRegistry(TemplateRegistry):
    """Local filesystem-backed template registry.
    
    Convenience wrapper around TemplateRegistry with LocalFSBackend.
    Stores templates as YAML files in a local directory.
    """
    
    def __init__(self, prompt_dir: str | Path) -> None:
        """Initialize local registry.
        
        Args:
            prompt_dir: Path to directory containing template YAML files
            
        Raises:
            FileNotFoundError: If prompt_dir doesn't exist
        """
        backend = LocalFSBackend(prompt_dir)
        super().__init__(backend)

    # Convenience passthrough methods to keep type checkers happy
    def load(self, template_id: str) -> TemplateSpec:  # type: ignore[override]
        """Load a template by ID from local filesystem.
        
        Args:
            template_id: The template ID to load
            
        Returns:
            TemplateSpec for the requested template
            
        Raises:
            TemplateNotFound: If no template with given ID exists
        """
        return super().load(template_id)

    def list_ids(self) -> Iterable[str]:  # type: ignore[override]
        """List all template IDs in the local filesystem.
        
        Returns:
            Iterable of template IDs
        """
        return super().list_ids()
