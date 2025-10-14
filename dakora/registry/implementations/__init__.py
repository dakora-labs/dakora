"""Concrete registry implementations."""
from .local import LocalRegistry
from .azure import AzureRegistry

__all__ = ["LocalRegistry", "AzureRegistry"]
