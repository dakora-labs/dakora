"""Azure Blob Storage template registry implementation."""
from __future__ import annotations
from typing import Optional

try:
    from azure.storage.blob import BlobServiceClient  # type: ignore
    from azure.core.exceptions import ResourceNotFoundError, HttpResponseError, ServiceRequestError  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime when user selects azure registry
    # Provide lightweight stubs so static type checkers know the attributes exist
    class _BlobServiceClientStub:  # pragma: no cover - runtime only when azure libs missing
        @classmethod
        def from_connection_string(cls, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ImportError("Azure support requires installing optional dependencies: pip install 'dakora[azure]'")

        def __init__(self, *_, **__):  # type: ignore[no-untyped-def]
            raise ImportError("Azure support requires installing optional dependencies: pip install 'dakora[azure]'")

        def get_container_client(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ImportError("Azure support requires installing optional dependencies: pip install 'dakora[azure]'")

    BlobServiceClient = _BlobServiceClientStub  # type: ignore
    ResourceNotFoundError = HttpResponseError = ServiceRequestError = Exception  # type: ignore

    class _DefaultAzureCredentialStub:  # pragma: no cover
        def __init__(self, *_, **__):  # type: ignore[no-untyped-def]
            raise ImportError("Azure support requires installing optional dependencies: pip install 'dakora[azure]'")

    DefaultAzureCredential = _DefaultAzureCredentialStub  # type: ignore

from ..core import TemplateRegistry
from ..backends import AzureBlobBackend
from ..serialization import parse_yaml
from ...exceptions import RegistryError, TemplateNotFound
from ...model import TemplateSpec

__all__ = ["AzureRegistry"]


class AzureRegistry(TemplateRegistry):
    """Azure Blob Storage-backed template registry.
    
    Supports multiple authentication methods:
    1. Connection string via explicit parameter or AZURE_STORAGE_CONNECTION_STRING env var
    2. Azure AD (DefaultAzureCredential) with account_url
    3. Managed Identity (when running in Azure) via DefaultAzureCredential
    
    Supports blob versioning for audit trails and template history.
    When versioning is enabled on the container, each save creates a new version
    instead of overwriting, allowing you to track changes and restore previous versions.
    """

    def __init__(
        self,
        container: str,
        prefix: str = "prompts/",
        connection_string: Optional[str] = None,
        account_url: Optional[str] = None,
        enable_versioning: bool = True,
    ) -> None:
        """Initialize Azure Blob Storage registry.
        
        Args:
            container: Azure storage container name
            prefix: Prefix for blob paths (default: "prompts/")
            connection_string: Azure storage connection string
            account_url: Azure storage account URL (uses DefaultAzureCredential)
            enable_versioning: If True, leverages blob versioning (requires container versioning enabled)
            
        Raises:
            RegistryError: If initialization or authentication fails
        """
        self.container_name = container
        self.prefix = prefix.rstrip('/') + '/' if prefix else ""
        self.enable_versioning = enable_versioning

        try:
            if connection_string:
                self._client = BlobServiceClient.from_connection_string(connection_string)
            elif account_url:
                credential = DefaultAzureCredential()  # attempts multiple auth methods
                # mypy/pylance: when using stub fallback, credential type won't match
                self._client = BlobServiceClient(account_url=account_url, credential=credential)  # type: ignore[arg-type]
            else:
                import os
                conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
                if not conn:
                    raise RegistryError(
                        "Azure registry requires either connection_string, account_url, or AZURE_STORAGE_CONNECTION_STRING env var"
                    )
                self._client = BlobServiceClient.from_connection_string(conn)

            self._container = self._client.get_container_client(self.container_name)
            self._validate_access()
            backend = AzureBlobBackend(self._container, self.prefix, enable_versioning=self.enable_versioning)
            super().__init__(backend)
        except RegistryError:
            raise
        except ServiceRequestError as e:  # network or DNS issues
            raise RegistryError(f"Failed to reach Azure Blob service: {e}") from e
        except ResourceNotFoundError as e:
            raise RegistryError(f"Container '{self.container_name}' not found") from e
        except Exception as e:  # pragma: no cover - broad fallback
            raise RegistryError(f"Failed to initialize AzureRegistry: {e}") from e

    # --- Internal helpers -------------------------------------------------
    def _validate_access(self) -> None:
        """Validate both read and write access to the container.
        
        Performs a lightweight test to ensure the registry can function properly.
        This catches permission issues early rather than failing during save operations.
        
        Also checks if blob versioning is enabled when requested.
        """
        try:
            # Step 1: Verify read access by getting container properties
            _ = self._container.get_container_properties()
            
            # Step 2: Check if versioning is enabled on the container
            if self.enable_versioning:
                import warnings
                try:
                    # Try to list blobs with version info to detect if versioning is available
                    _ = list(self._container.list_blobs(max_results=1, include=['versions']))
                except Exception:
                    # If include=['versions'] fails, versioning might not be enabled
                    warnings.warn(
                        f"Blob versioning may not be enabled on container '{self.container_name}'. "
                        f"Enable versioning on your storage account to use version history features. "
                        f"See: https://learn.microsoft.com/en-us/azure/storage/blobs/versioning-overview",
                        stacklevel=2
                    )
            
            # Step 3: Verify write access with a test blob
            # Use a hidden marker file that won't interfere with templates
            test_blob_name = f"{self.prefix}.dakora_write_test"
            test_blob = self._container.get_blob_client(test_blob_name)
            
            try:
                # Attempt to write
                test_blob.upload_blob(b"write-test", overwrite=True)
                # Clean up immediately
                test_blob.delete_blob()
            except HttpResponseError as write_error:
                if getattr(write_error, 'status_code', None) == 403:
                    raise RegistryError(
                        f"Write access denied to container '{self.container_name}'. "
                        f"This registry requires both read and write permissions. "
                        f"Check your RBAC role assignments (need 'Storage Blob Data Contributor' or similar)."
                    ) from write_error
                # Re-raise other HTTP errors
                raise
                
        except HttpResponseError as e:
            # Handle read permission errors
            if getattr(e, 'status_code', None) == 403:
                raise RegistryError(
                    f"Read access denied to container '{self.container_name}'. Check RBAC or credentials."
                ) from e
            raise

    # --- Versioning support --------------------------------------------
    def list_versions(self, template_id: str) -> list[dict]:
        """List all versions of a template.
        
        Requires blob versioning to be enabled on the container.
        
        Args:
            template_id: The template ID to get version history for
            
        Returns:
            List of version metadata dicts with keys:
            - version_id: Azure version identifier
            - last_modified: When this version was created
            - is_current: Whether this is the current version
            - size: Blob size in bytes
            
        Raises:
            RegistryError: If versioning is not enabled or template doesn't exist
        """
        if not self.enable_versioning:
            raise RegistryError(
                "Versioning is disabled for this registry. "
                "Initialize with enable_versioning=True to use version features."
            )
        
        filename = f"{template_id}.yaml"
        blob_name = f"{self.prefix}{filename}" if self.prefix else filename
        
        try:
            versions = []
            # List all versions of the blob (requires container versioning enabled)
            version_list = self._container.list_blobs(
                name_starts_with=blob_name,
                include=['versions']
            )
            
            for blob in version_list:
                if blob.name == blob_name:
                    versions.append({
                        'version_id': blob.version_id,
                        'last_modified': blob.last_modified,
                        'is_current': getattr(blob, 'is_current_version', True),
                        'size': blob.size,
                    })
            
            if not versions:
                raise RegistryError(f"Template '{template_id}' not found or has no versions")
                
            # Sort by last_modified, newest first
            versions.sort(key=lambda v: v['last_modified'], reverse=True)
            return versions
            
        except HttpResponseError as e:
            if getattr(e, 'status_code', None) == 404:
                raise RegistryError(f"Template '{template_id}' not found") from e
            raise RegistryError(f"Failed to list versions for '{template_id}': {e}") from e
        except Exception as e:
            raise RegistryError(f"Error listing versions for '{template_id}': {e}") from e

    def load_version(self, template_id: str, version_id: str) -> TemplateSpec:
        """Load a specific version of a template.
        
        Requires blob versioning to be enabled on the container.
        
        Args:
            template_id: The template ID
            version_id: The Azure version ID to load
            
        Returns:
            TemplateSpec for the specified version
            
        Raises:
            RegistryError: If versioning is not enabled
            TemplateNotFound: If template or version doesn't exist
        """
        if not self.enable_versioning:
            raise RegistryError(
                "Versioning is disabled for this registry. "
                "Initialize with enable_versioning=True to use version features."
            )
        
        filename = f"{template_id}.yaml"
        blob_name = f"{self.prefix}{filename}" if self.prefix else filename
        
        try:
            blob = self._container.get_blob_client(blob_name)
            # Download specific version
            content = blob.download_blob(version_id=version_id).readall().decode('utf-8')
            
            data = parse_yaml(content)
            spec = TemplateSpec.model_validate(data)
            
            # Normalize trailing newlines (consistent with base registry)
            if spec.template.endswith('\n'):
                spec.template = spec.template.rstrip('\n')
                
            return spec
            
        except ResourceNotFoundError as e:
            raise TemplateNotFound(f"{template_id} (version: {version_id})") from e
        except HttpResponseError as e:
            if getattr(e, 'status_code', None) == 404:
                raise TemplateNotFound(f"{template_id} (version: {version_id})") from e
            raise RegistryError(f"Failed to load version {version_id} of '{template_id}': {e}") from e
        except Exception as e:
            raise RegistryError(f"Error loading version {version_id} of '{template_id}': {e}") from e

    def restore_version(self, template_id: str, version_id: str) -> None:
        """Restore a previous version of a template as the current version.
        
        This loads the specified version and saves it as a new current version,
        preserving the version history.
        
        Args:
            template_id: The template ID
            version_id: The Azure version ID to restore
            
        Raises:
            RegistryError: If versioning is not enabled
            TemplateNotFound: If template or version doesn't exist
        """
        spec = self.load_version(template_id, version_id)
        self.save(spec)  # Save as new current version

    def __repr__(self) -> str:  # pragma: no cover - repr trivial
        versioning_status = "versioning-enabled" if self.enable_versioning else "versioning-disabled"
        return f"AzureRegistry(container='{self.container_name}', prefix='{self.prefix}', {versioning_status})"
