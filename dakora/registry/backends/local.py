"""Local filesystem storage backend."""
from __future__ import annotations
from typing import Iterable
from pathlib import Path

__all__ = ["LocalFSBackend"]


class LocalFSBackend:
    """Local filesystem storage backend for templates.
    
    Stores templates as YAML files in a local directory, supporting
    recursive directory structures.
    """
    
    def __init__(self, root: str | Path) -> None:
        """Initialize local filesystem backend.
        
        Args:
            root: Root directory path for template storage
            
        Raises:
            FileNotFoundError: If root directory doesn't exist
        """
        self.root = Path(root).resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"prompt_dir not found: {self.root}")

    def list(self) -> Iterable[str]:
        """List all YAML files recursively.
        
        Returns:
            Iterable of relative file paths (POSIX format)
        """
        for p in self.root.rglob('*.y*ml'):
            rel = p.relative_to(self.root).as_posix()
            yield rel

    def read_text(self, name: str) -> str:
        """Read file contents.
        
        Args:
            name: Relative file path
            
        Returns:
            File contents as UTF-8 string
        """
        return (self.root / name).read_text(encoding='utf-8')

    def write_text(self, name: str, data: str) -> None:
        """Write file contents, creating directories as needed.
        
        Args:
            name: Relative file path
            data: UTF-8 string content to write
        """
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')

    def exists(self, name: str) -> bool:
        """Check if file exists.
        
        Args:
            name: Relative file path
            
        Returns:
            True if file exists, False otherwise
        """
        return (self.root / name).exists()
