"""
Comprehensive tests for Azure Blob Storage registry implementation.

Includes both unit tests (with mocking) and integration tests (with Vault config).
These tests use mocking to avoid requiring actual Azure credentials.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from pathlib import Path

from dakora.exceptions import RegistryError, TemplateNotFound, DakoraError
from dakora.model import TemplateSpec
from dakora.vault import Vault

# Skip all tests if Azure dependencies are not installed
pytest.importorskip("azure.storage.blob")
pytest.importorskip("azure.identity")

from dakora.registry.implementations.azure import AzureRegistry  # noqa: E402


class MockBlob:
    """Mock Azure Blob object"""
    def __init__(self, name, version_id=None, last_modified=None, size=1024, is_current=True):
        self.name = name
        self.version_id = version_id or "v1"
        self.last_modified = last_modified or datetime.now(timezone.utc)
        self.size = size
        self.is_current_version = is_current


class MockBlobClient:
    """Mock Azure BlobClient"""
    def __init__(self, content="id: test\nversion: '1.0.0'\ntemplate: 'Hello'\ninputs: {}\n"):
        self.content = content
        self.uploaded_data = None
        self.deleted = False
        
    def download_blob(self, version_id=None):
        """Mock download_blob method"""
        mock_download = Mock()
        mock_download.readall.return_value = self.content.encode('utf-8')
        return mock_download
    
    def upload_blob(self, data, overwrite=False):
        """Mock upload_blob method"""
        self.uploaded_data = data
        return Mock()
    
    def delete_blob(self):
        """Mock delete_blob method"""
        self.deleted = True


class MockContainerClient:
    """Mock Azure ContainerClient"""
    def __init__(self, exists=True, writable=True, versioning_enabled=True):
        self.exists = exists
        self.writable = writable
        self.versioning_enabled = versioning_enabled
        self.blobs = {}
        self.blob_clients = {}
        
    def get_container_properties(self):
        """Mock get_container_properties"""
        if not self.exists:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Container not found")
        return {"name": "test-container"}
    
    def list_blobs(self, name_starts_with=None, include=None, max_results=None):
        """Mock list_blobs"""
        blobs = []
        for name, blob in self.blobs.items():
            if name_starts_with is None or name.startswith(name_starts_with):
                if include and 'versions' in include:
                    if not self.versioning_enabled:
                        raise Exception("Versioning not enabled")
                blobs.append(blob)
        
        if max_results:
            return blobs[:max_results]
        return blobs
    
    def get_blob_client(self, blob_name):
        """Mock get_blob_client"""
        if blob_name not in self.blob_clients:
            self.blob_clients[blob_name] = MockBlobClient()
        return self.blob_clients[blob_name]


class MockBlobServiceClient:
    """Mock Azure BlobServiceClient"""
    def __init__(self, container_client=None):
        self._container_client = container_client or MockContainerClient()
    
    def get_container_client(self, container_name):
        """Mock get_container_client"""
        return self._container_client
    
    @classmethod
    def from_connection_string(cls, connection_string):
        """Mock from_connection_string"""
        return cls()


# ============================================================================
# Initialization Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_azure_registry_init_with_connection_string(mock_blob_service):
    """Test initialization with connection string"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test123"
    )
    
    assert registry.container_name == "test-container"
    assert registry.prefix == "prompts/"
    assert registry.enable_versioning is True
    mock_blob_service.from_connection_string.assert_called_once()


@patch('dakora.registry.implementations.azure.BlobServiceClient')
@patch('dakora.registry.implementations.azure.DefaultAzureCredential')
def test_azure_registry_init_with_account_url(mock_credential, mock_blob_service):
    """Test initialization with account URL and DefaultAzureCredential"""
    mock_blob_service.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        account_url="https://testaccount.blob.core.windows.net",
        prefix="templates/"
    )
    
    assert registry.container_name == "test-container"
    assert registry.prefix == "templates/"
    mock_credential.assert_called_once()
    mock_blob_service.assert_called_once()


@patch('dakora.registry.implementations.azure.BlobServiceClient')
@patch.dict('os.environ', {'AZURE_STORAGE_CONNECTION_STRING': 'test-conn-string'})
def test_azure_registry_init_with_env_var(mock_blob_service):
    """Test initialization with environment variable"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(container="test-container")
    
    assert registry.container_name == "test-container"
    mock_blob_service.from_connection_string.assert_called_once_with('test-conn-string')


@patch('dakora.registry.implementations.azure.BlobServiceClient')
@patch.dict('os.environ', {}, clear=True)
def test_azure_registry_init_no_credentials_raises_error(mock_blob_service):
    """Test initialization without credentials raises RegistryError"""
    with pytest.raises(RegistryError, match="requires either connection_string"):
        AzureRegistry(container="test-container")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_azure_registry_init_container_not_found(mock_blob_service):
    """Test initialization with non-existent container raises error"""
    container = MockContainerClient(exists=False)
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    with pytest.raises(RegistryError, match="Container 'test-container' not found"):
        AzureRegistry(
            container="test-container",
            connection_string="test"
        )


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_azure_registry_init_with_custom_prefix(mock_blob_service):
    """Test initialization with custom prefix"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        prefix="my-prompts",
        enable_versioning=False
    )
    
    assert registry.prefix == "my-prompts/"
    assert registry.enable_versioning is False


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_azure_registry_init_with_empty_prefix(mock_blob_service):
    """Test initialization with empty prefix"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        prefix=""
    )
    
    assert registry.prefix == ""


# ============================================================================
# Access Validation Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_validate_access_read_permission_denied(mock_blob_service):
    """Test validation fails when read access is denied"""
    from azure.core.exceptions import HttpResponseError
    
    container = MockContainerClient()
    mock_response = Mock()
    mock_response.status_code = 403
    error = HttpResponseError(response=mock_response)
    container.get_container_properties = Mock(side_effect=error)
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    with pytest.raises(RegistryError, match="Read access denied"):
        AzureRegistry(container="test-container", connection_string="test")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_validate_access_write_permission_denied(mock_blob_service):
    """Test validation fails when write access is denied"""
    from azure.core.exceptions import HttpResponseError
    
    container = MockContainerClient()
    blob_client = MockBlobClient()
    
    # Make upload raise 403 error
    mock_response = Mock()
    mock_response.status_code = 403
    error = HttpResponseError(response=mock_response)
    blob_client.upload_blob = Mock(side_effect=error)
    
    container.get_blob_client = Mock(return_value=blob_client)
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    with pytest.raises(RegistryError, match="Write access denied"):
        AzureRegistry(container="test-container", connection_string="test")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_validate_access_versioning_warning(mock_blob_service):
    """Test warning is raised when versioning is not available"""
    import warnings
    
    container = MockContainerClient(versioning_enabled=False)
    
    # Mock list_blobs to raise exception when include=['versions']
    def failing_list_blobs(name_starts_with=None, include=None, max_results=None):
        if include and 'versions' in include:
            raise Exception("Versioning not supported")
        return []
    
    container.list_blobs = failing_list_blobs  # type: ignore
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _registry = AzureRegistry(
            container="test-container",
            connection_string="test",
            enable_versioning=True
        )
        
        # Check that a warning was raised about versioning
        assert len(w) > 0
        assert "versioning may not be enabled" in str(w[0].message).lower()


# ============================================================================
# Versioning Feature Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_list_versions_success(mock_blob_service):
    """Test listing all versions of a template"""
    container = MockContainerClient()
    
    # Create mock versions
    blob1 = MockBlob("prompts/test.yaml", version_id="v1", 
                     last_modified=datetime(2024, 1, 1, tzinfo=timezone.utc), is_current=False)
    blob2 = MockBlob("prompts/test.yaml", version_id="v2",
                     last_modified=datetime(2024, 1, 2, tzinfo=timezone.utc), is_current=True)
    
    container.blobs = {
        "prompts/test.yaml": blob1,
        "prompts/test.yaml_v2": blob2
    }
    
    # Override list_blobs method to return versions
    original_list = container.list_blobs
    
    def mock_list_blobs(name_starts_with=None, include=None, max_results=None):
        if include and 'versions' in include:
            return [blob1, blob2]
        return original_list(name_starts_with, include, max_results)
    
    container.list_blobs = mock_list_blobs  # type: ignore
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    versions = registry.list_versions("test")
    
    assert len(versions) == 2
    assert versions[0]['version_id'] == "v2"  # Newest first
    assert versions[1]['version_id'] == "v1"
    assert versions[0]['is_current'] is True
    assert versions[1]['is_current'] is False


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_list_versions_versioning_disabled(mock_blob_service):
    """Test list_versions raises error when versioning is disabled"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        enable_versioning=False
    )
    
    with pytest.raises(RegistryError, match="Versioning is disabled"):
        registry.list_versions("test")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_list_versions_template_not_found(mock_blob_service):
    """Test list_versions raises error when template doesn't exist"""
    container = MockContainerClient()
    container.list_blobs = Mock(return_value=[])
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    with pytest.raises(RegistryError, match="not found or has no versions"):
        registry.list_versions("nonexistent")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_load_version_success(mock_blob_service):
    """Test loading a specific version of a template"""
    container = MockContainerClient()
    blob_client = MockBlobClient(
        content="id: test\nversion: '1.0.0'\ntemplate: 'Hello {{ name }}'\ninputs:\n  name:\n    type: string\n"
    )
    container.get_blob_client = Mock(return_value=blob_client)
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    spec = registry.load_version("test", "v1")
    
    assert spec.id == "test"
    assert spec.version == "1.0.0"
    assert spec.template == "Hello {{ name }}"


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_load_version_versioning_disabled(mock_blob_service):
    """Test load_version raises error when versioning is disabled"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        enable_versioning=False
    )
    
    with pytest.raises(RegistryError, match="Versioning is disabled"):
        registry.load_version("test", "v1")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_load_version_not_found(mock_blob_service):
    """Test load_version raises TemplateNotFound when version doesn't exist"""
    from azure.core.exceptions import ResourceNotFoundError
    
    container = MockContainerClient()
    blob_client = MockBlobClient()
    blob_client.download_blob = Mock(side_effect=ResourceNotFoundError("Not found"))
    container.get_blob_client = Mock(return_value=blob_client)
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    with pytest.raises(TemplateNotFound, match="test.*version: v999"):
        registry.load_version("test", "v999")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_restore_version_success(mock_blob_service):
    """Test restoring a previous version"""
    container = MockContainerClient()
    
    # Mock blob client for reading old version
    old_version_content = "id: test\nversion: '1.0.0'\ntemplate: 'Old version'\ninputs: {}\n"
    blob_client = MockBlobClient(content=old_version_content)
    container.get_blob_client = Mock(return_value=blob_client)
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    # Mock the save method to track calls
    with patch.object(registry, 'save') as mock_save:
        registry.restore_version("test", "v1")
        
        # Verify save was called with the loaded spec
        assert mock_save.called
        saved_spec = mock_save.call_args[0][0]
        assert isinstance(saved_spec, TemplateSpec)
        assert saved_spec.template == "Old version"


# ============================================================================
# Network Error Handling Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_network_error_during_init(mock_blob_service):
    """Test network errors are properly handled during initialization"""
    from azure.core.exceptions import ServiceRequestError
    
    mock_blob_service.from_connection_string.side_effect = ServiceRequestError("Network error")
    
    with pytest.raises(RegistryError, match="Failed to reach Azure Blob service"):
        AzureRegistry(container="test-container", connection_string="test")


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_http_error_during_list_versions(mock_blob_service):
    """Test HTTP errors during version listing"""
    import warnings
    from azure.core.exceptions import HttpResponseError
    
    container = MockContainerClient()
    mock_response = Mock()
    mock_response.status_code = 500
    error = HttpResponseError(response=mock_response)
    container.list_blobs = Mock(side_effect=error)
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    # Suppress the versioning warning during initialization (expected in mock environment)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        registry = AzureRegistry(container="test-container", connection_string="test")
    
    with pytest.raises(RegistryError, match="Failed to list versions"):
        registry.list_versions("test")


# ============================================================================
# Template Normalization Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_load_version_strips_trailing_newlines(mock_blob_service):
    """Test that trailing newlines are stripped from templates"""
    container = MockContainerClient()
    
    # Template with actual trailing newlines (not escaped)
    content = "id: test\nversion: '1.0.0'\ntemplate: |\n  Hello\n\ninputs: {}\n"
    blob_client = MockBlobClient(content=content)
    container.get_blob_client = Mock(return_value=blob_client)
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    spec = registry.load_version("test", "v1")
    
    # Trailing newlines should be stripped
    assert spec.template == "Hello"


# ============================================================================
# Repr Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_repr_with_versioning_enabled(mock_blob_service):
    """Test __repr__ with versioning enabled"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        prefix="prompts/",
        enable_versioning=True
    )
    
    repr_str = repr(registry)
    assert "test-container" in repr_str
    assert "prompts/" in repr_str
    assert "versioning-enabled" in repr_str


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_repr_with_versioning_disabled(mock_blob_service):
    """Test __repr__ with versioning disabled"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    registry = AzureRegistry(
        container="test-container",
        connection_string="test",
        enable_versioning=False
    )
    
    repr_str = repr(registry)
    assert "versioning-disabled" in repr_str


# ============================================================================
# Integration with Base Registry Tests
# ============================================================================

@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_azure_registry_inherits_from_base(mock_blob_service):
    """Test that AzureRegistry properly inherits base functionality"""
    container = MockContainerClient()
    
    # Add a test blob
    test_blob = MockBlob("prompts/greeting.yaml")
    container.blobs = {"prompts/greeting.yaml": test_blob}
    
    blob_content = """id: greeting
version: '1.0.0'
template: 'Hello {{ name }}'
inputs:
  name:
    type: string
    required: true
"""
    blob_client = MockBlobClient(content=blob_content)
    container.blob_clients["prompts/greeting.yaml"] = blob_client
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    # Test that base methods work (list is implemented by backend)
    # The load method should work through the base class
    spec = registry.load("greeting")
    assert spec.id == "greeting"
    assert "name" in spec.inputs


# ============================================================================
# Integration Tests - Vault Configuration
# ============================================================================

def test_vault_azure_config_missing_container(tmp_path: Path):
    """Test that Vault rejects Azure config without container"""
    cfg = tmp_path / "dakora.yaml"
    cfg.write_text("registry: azure\n", encoding="utf-8")
    
    with pytest.raises(DakoraError, match="missing azure_container"):
        Vault(str(cfg))


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_vault_azure_config_with_container(mock_blob_service, tmp_path: Path):
    """Test that Vault accepts Azure config with container"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    cfg = tmp_path / "dakora.yaml"
    config_content = """registry: azure
azure_container: test-container
azure_connection_string: DefaultEndpointsProtocol=https;AccountName=test;AccountKey=fake
"""
    cfg.write_text(config_content, encoding="utf-8")
    
    # Should successfully create Vault with Azure registry
    vault = Vault(str(cfg))
    assert vault.config["registry"] == "azure"
    assert vault.config["azure_container"] == "test-container"


@patch('dakora.registry.implementations.azure.BlobServiceClient')
def test_vault_azure_config_with_custom_prefix(mock_blob_service, tmp_path: Path):
    """Test Vault Azure config with custom prefix"""
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient()
    
    cfg = tmp_path / "dakora.yaml"
    config_content = """registry: azure
azure_container: test-container
azure_prefix: custom-prompts/
azure_connection_string: DefaultEndpointsProtocol=https;AccountName=test;AccountKey=fake
"""
    cfg.write_text(config_content, encoding="utf-8")
    
    vault = Vault(str(cfg))
    assert vault.config["azure_prefix"] == "custom-prompts/"


def test_vault_local_config_still_works(tmp_path: Path):
    """Test that local registry configuration continues to work alongside Azure"""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "demo.yaml").write_text(
        "id: demo\nversion: '1'\ntemplate: 'hi'\ninputs: {}\n", 
        encoding="utf-8"
    )
    
    cfg = tmp_path / "dakora.yaml"
    cfg.write_text(f"registry: local\nprompt_dir: {prompts.as_posix()}\n", encoding="utf-8")
    
    vault = Vault(str(cfg))
    assert 'demo' in vault.list()
