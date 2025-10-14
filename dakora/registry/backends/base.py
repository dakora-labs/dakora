"""Storage backend protocol definition."""
from __future__ import annotations
from typing import Iterable, Protocol

__all__ = ["StorageBackend"]


class StorageBackend(Protocol):
    """Protocol defining the interface for template storage backends.
    
    All backend implementations must provide these methods to support
    template registry operations.
    """
    
    def list(self) -> Iterable[str]:
        """List all template file names in the storage.
        
        Returns:
            Iterable of relative file paths/names
        """
        ...
    
    def read_text(self, name: str) -> str:
        """Read template file contents as text.
        
        Args:
            name: Relative file path/name
            
        Returns:
            File contents as UTF-8 string
        """
        ...
    
    def write_text(self, name: str, data: str) -> None:
        """Write template file contents.
        
        Args:
            name: Relative file path/name
            data: UTF-8 string content to write
        """
        ...
    
    def exists(self, name: str) -> bool:
        """Check if a template file exists.
        
        Args:
            name: Relative file path/name
            
        Returns:
            True if file exists, False otherwise
        """
        ...
