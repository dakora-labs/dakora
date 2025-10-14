"""Azure Blob Storage backend."""
from __future__ import annotations
from typing import Iterable

__all__ = ["AzureBlobBackend"]


class AzureBlobBackend:
    """Azure Blob Storage backend for templates.
    
    Provides template storage using Azure Blob Storage, with support
    for blob versioning when enabled on the container.
    
    Expects a container_client from Azure SDK exposing:
    - list_blobs(name_starts_with=...)
    - get_blob_client(blob_name)
    
    Supports blob versioning when enabled - each write creates a new version
    instead of overwriting, providing audit trails and the ability to restore
    previous template versions.
    """
    
    def __init__(
        self,
        container_client,
        prefix: str = "",
        enable_versioning: bool = True
    ) -> None:  # pragma: no cover - runtime only
        """Initialize Azure Blob Storage backend.
        
        Args:
            container_client: Azure BlobContainerClient instance
            prefix: Optional prefix for blob paths (e.g., "prompts/")
            enable_versioning: If True, leverages blob versioning for audit trails
        """
        self._container = container_client
        self.prefix = prefix.rstrip('/') + '/' if prefix else ''
        self.enable_versioning = enable_versioning

    def _full(self, name: str) -> str:
        """Convert relative name to full blob path with prefix.
        
        Args:
            name: Relative file name
            
        Returns:
            Full blob path including prefix
        """
        return f"{self.prefix}{name}" if self.prefix else name

    def list(self) -> Iterable[str]:  # pragma: no cover - azure runtime
        """List all YAML blobs.
        
        Returns:
            Iterable of relative blob names (without prefix)
        """
        for blob in self._container.list_blobs(name_starts_with=self.prefix or None):
            name = getattr(blob, 'name', '')
            if name.endswith(('.yaml', '.yml')):
                # Remove prefix for registry-level name
                rel = name[len(self.prefix):] if self.prefix and name.startswith(self.prefix) else name
                yield rel

    def read_text(self, name: str) -> str:  # pragma: no cover
        """Read blob contents.
        
        Args:
            name: Relative blob name
            
        Returns:
            Blob contents as UTF-8 string
        """
        blob = self._container.get_blob_client(self._full(name))
        return blob.download_blob().readall().decode('utf-8')

    def write_text(self, name: str, data: str) -> None:  # pragma: no cover
        """Write blob contents.
        
        When versioning is enabled and the container has blob versioning enabled,
        Azure automatically creates a new version when overwriting. This provides
        automatic audit trails and the ability to restore previous versions.
        
        Note: Container-level versioning must be enabled in Azure Storage for this to work.
        
        Args:
            name: Relative blob name
            data: UTF-8 string content to write
        """
        blob = self._container.get_blob_client(self._full(name))
        # When container versioning is enabled, overwrite=True creates a new version automatically
        # The old version is preserved as a previous version, not deleted
        blob.upload_blob(data.encode('utf-8'), overwrite=True)

    def exists(self, name: str) -> bool:  # pragma: no cover
        """Check if blob exists.
        
        Args:
            name: Relative blob name
            
        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob = self._container.get_blob_client(self._full(name))
            blob.get_blob_properties()
            return True
        except Exception:
            return False
