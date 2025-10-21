"""Tests for template deletion functionality across registries."""
import tempfile
from pathlib import Path
import yaml
import pytest
from unittest.mock import Mock, patch

from dakora_server.core.registry import LocalRegistry
from dakora_server.core.vault import Vault
from dakora_server.core.exceptions import TemplateNotFound

# Skip Azure tests if dependencies not installed
pytest.importorskip("azure.storage.blob", reason="Azure dependencies not installed")
pytest.importorskip("azure.identity", reason="Azure dependencies not installed")

from dakora_server.core.registry.implementations.azure import AzureRegistry


# ============================================================================
# Local Registry Delete Tests
# ============================================================================

def test_delete_template_local_registry():
    """Test deleting a template from local filesystem registry"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        
        # Create a test template
        template_file = prompts_dir / "test-template.yaml"
        template_file.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        registry = LocalRegistry(prompts_dir)
        
        # Verify template exists
        assert "test-template" in list(registry.list_ids())
        assert template_file.exists()
        
        # Delete the template
        registry.delete("test-template")
        
        # Verify template is gone
        assert "test-template" not in list(registry.list_ids())
        assert not template_file.exists()


def test_delete_nonexistent_template_local_registry():
    """Test that deleting non-existent template raises TemplateNotFound"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        registry = LocalRegistry(prompts_dir)
        
        with pytest.raises(TemplateNotFound, match="nonexistent"):
            registry.delete("nonexistent")


def test_delete_template_with_yml_extension():
    """Test deleting a template with .yml extension"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        
        # Create template with .yml extension
        template_file = prompts_dir / "test-template.yml"
        template_file.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        registry = LocalRegistry(prompts_dir)
        
        # Verify template exists
        assert "test-template" in list(registry.list_ids())
        
        # Delete should work
        registry.delete("test-template")
        
        # Verify it's gone
        assert "test-template" not in list(registry.list_ids())
        assert not template_file.exists()


def test_delete_template_in_subdirectory():
    """Test deleting a template in a subdirectory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        subdir = prompts_dir / "category"
        subdir.mkdir()
        
        # Create template in subdirectory
        template_file = subdir / "test-template.yaml"
        template_file.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        registry = LocalRegistry(prompts_dir)
        
        # Verify template exists
        assert "test-template" in list(registry.list_ids())
        
        # Delete should work even in subdirectory
        registry.delete("test-template")
        
        # Verify it's gone
        assert "test-template" not in list(registry.list_ids())
        assert not template_file.exists()


def test_delete_template_cache_invalidation():
    """Test that deleting a template invalidates the vault cache"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        
        # Create a test template
        template_file = prompts_dir / "test-template.yaml"
        template_file.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        config = {
            "registry": "local",
            "prompt_dir": str(prompts_dir),
        }
        
        config_path = Path(tmpdir) / "dakora.yaml"
        config_path.write_text(yaml.safe_dump(config))
        
        vault = Vault(str(config_path))
        
        # Load template into cache
        vault.get("test-template")
        
        # Delete via vault (should invalidate cache)
        vault.delete("test-template")
        
        # Verify template is gone
        with pytest.raises(TemplateNotFound):
            vault.get("test-template")


# ============================================================================
# Azure Registry Delete Tests (with mocking)
# ============================================================================

class MockBlobClient:
    """Mock Azure BlobClient for testing"""
    def __init__(self, content="", exists=True, deleted=False):
        self.content = content
        self.exists_flag = exists
        self.deleted = deleted
        self.uploaded_data = None
    
    def get_blob_properties(self):
        """Mock get_blob_properties"""
        if not self.exists_flag or self.deleted:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
        return Mock(name="test-blob.yaml")
    
    def download_blob(self, version_id=None):
        """Mock download_blob"""
        if not self.exists_flag or self.deleted:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
        mock_download = Mock()
        mock_download.readall.return_value = self.content.encode('utf-8')
        return mock_download
    
    def upload_blob(self, data, overwrite=False):
        """Mock upload_blob"""
        self.uploaded_data = data
        self.exists_flag = True
        return Mock()
    
    def delete_blob(self):
        """Mock delete_blob - simulates Azure versioning behavior"""
        if not self.exists_flag:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Blob not found")
        # In Azure with versioning: marks as deleted but version history remains
        self.deleted = True


class MockBlob:
    """Mock Azure Blob object"""
    def __init__(self, name, deleted=False):
        self.name = name
        self.deleted = deleted
        self.version_id = "v1"
        self.last_modified = "2024-01-01"
        self.size = 100


class MockContainerClient:
    """Mock Azure ContainerClient for testing"""
    def __init__(self, exists=True):
        self.exists = exists
        self.blobs = {}
        self.blob_clients = {}
    
    def get_container_properties(self):
        """Mock get_container_properties"""
        if not self.exists:
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("Container not found")
        return {"name": "test-container"}
    
    def list_blobs(self, name_starts_with=None, include=None):
        """Mock list_blobs - excludes deleted blobs in standard listing"""
        blobs = []
        for name, blob in self.blobs.items():
            if name_starts_with is None or name.startswith(name_starts_with):
                # Standard list_blobs does NOT show deleted blobs
                if not blob.deleted:
                    blobs.append(blob)
        return blobs
    
    def get_blob_client(self, blob_name):
        """Mock get_blob_client"""
        if blob_name not in self.blob_clients:
            self.blob_clients[blob_name] = MockBlobClient(exists=False)
        return self.blob_clients[blob_name]


class MockBlobServiceClient:
    """Mock Azure BlobServiceClient"""
    def __init__(self, container=None):
        self.container = container or MockContainerClient()
    
    def get_container_client(self, container_name):
        """Mock get_container_client"""
        return self.container


@patch('dakora_server.core.registry.implementations.azure.BlobServiceClient')
def test_delete_template_azure_registry(mock_blob_service):
    """Test deleting a template from Azure registry"""
    container = MockContainerClient()
    
    # Setup a test blob
    blob_name = "prompts/test-template.yaml"
    test_blob = MockBlob(blob_name)
    container.blobs[blob_name] = test_blob
    
    blob_content = """id: test-template
version: '1.0.0'
template: 'Hello {{ name }}'
inputs:
  name:
    type: string
    required: true
"""
    blob_client = MockBlobClient(content=blob_content, exists=True)
    container.blob_clients[blob_name] = blob_client
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    # Verify template exists
    assert "test-template" in list(registry.list_ids())
    
    # Delete the template
    registry.delete("test-template")
    
    # Verify template is deleted (marked as deleted in mock)
    assert blob_client.deleted
    
    # Verify template no longer appears in listing (Azure behavior)
    test_blob.deleted = True
    assert "test-template" not in list(registry.list_ids())


@patch('dakora_server.core.registry.implementations.azure.BlobServiceClient')
def test_delete_nonexistent_template_azure_registry(mock_blob_service):
    """Test that deleting non-existent template from Azure raises TemplateNotFound"""
    container = MockContainerClient()
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(container="test-container", connection_string="test")
    
    with pytest.raises(TemplateNotFound, match="nonexistent"):
        registry.delete("nonexistent")


@patch('dakora_server.core.registry.implementations.azure.BlobServiceClient')
def test_delete_preserves_version_history_azure(mock_blob_service):
    """Test that Azure delete preserves version history (Option A behavior)"""
    container = MockContainerClient()
    
    blob_name = "prompts/test-template.yaml"
    test_blob = MockBlob(blob_name, deleted=False)
    container.blobs[blob_name] = test_blob
    
    blob_content = """id: test-template
version: '1.0.0'
template: 'Hello'
inputs: {}
"""
    blob_client = MockBlobClient(content=blob_content, exists=True)
    container.blob_clients[blob_name] = blob_client
    
    mock_blob_service.from_connection_string.return_value = MockBlobServiceClient(container)
    
    registry = AzureRegistry(
        container="test-container", 
        connection_string="test",
        enable_versioning=True
    )
    
    # Delete template
    registry.delete("test-template")
    
    # Blob should be marked as deleted (not removed from storage)
    assert blob_client.deleted
    
    # Template should not appear in standard listings
    test_blob.deleted = True
    assert "test-template" not in list(registry.list_ids())
    
    # Note: In real Azure, version history would still be accessible via
    # list_versions() API, but that's beyond scope of this delete test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
