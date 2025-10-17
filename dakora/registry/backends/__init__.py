"""Storage backend abstractions for template registries."""
from .base import StorageBackend
from .local import LocalFSBackend
from .azure import AzureBlobBackend

__all__ = ["StorageBackend", "LocalFSBackend", "AzureBlobBackend"]
