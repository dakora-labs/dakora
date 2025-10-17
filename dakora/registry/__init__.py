"""Template registry system for Dakora.

This package provides a flexible registry system for managing prompt templates
with support for multiple storage backends (local filesystem, Azure Blob Storage, etc.).

Public API:
-----------
Base Classes:
    Registry: Abstract base class for template registries
    
Core Implementation:
    TemplateRegistry: Main registry implementation with pluggable backends
    
Storage Backends:
    StorageBackend: Protocol defining the backend interface
    LocalFSBackend: Local filesystem storage backend
    AzureBlobBackend: Azure Blob Storage backend
    
Concrete Registries:
    LocalRegistry: Convenience wrapper for local filesystem storage
    AzureRegistry: Azure Blob Storage registry with versioning support

Usage Examples:
--------------
Local filesystem registry:
    >>> from dakora.registry import LocalRegistry
    >>> registry = LocalRegistry("./prompts")
    >>> spec = registry.load("my-template")

Or using the core implementation directly:
    >>> from dakora.registry import TemplateRegistry, LocalFSBackend
    >>> registry = TemplateRegistry(LocalFSBackend("./prompts"))
    >>> spec = registry.load("my-template")

Azure Blob Storage registry:
    >>> from dakora.registry import AzureRegistry
    >>> registry = AzureRegistry(
    ...     container="my-container",
    ...     connection_string="...",
    ...     enable_versioning=True
    ... )
    >>> spec = registry.load("my-template")
    >>> versions = registry.list_versions("my-template")
"""
from __future__ import annotations

# Base classes
from .base import Registry

# Core implementation
from .core import TemplateRegistry

# Storage backends
from .backends import StorageBackend, LocalFSBackend, AzureBlobBackend

# Concrete registry implementations
from .implementations import LocalRegistry, AzureRegistry

__all__ = [
    # Base classes
    "Registry",
    
    # Core
    "TemplateRegistry",
    
    # Backends
    "StorageBackend",
    "LocalFSBackend",
    "AzureBlobBackend",
    
    # Implementations
    "LocalRegistry",
    "AzureRegistry",
]
