"""Integration tests for template deletion API endpoint."""
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

from dakora_server.main import app
from dakora_server.config import get_vault
from dakora_server.core.vault import Vault


@pytest.fixture
def test_vault_with_template() -> Generator[tuple[Vault, Path], None, None]:
    """Create a test vault with a sample template"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        
        # Create test templates
        template1 = prompts_dir / "test-template.yaml"
        template1.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "description: 'Test template for deletion'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        template2 = prompts_dir / "another-template.yaml"
        template2.write_text(
            "id: another-template\n"
            "version: '1.0.0'\n"
            "description: 'Another test template'\n"
            "template: 'Goodbye {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )
        
        vault = Vault(prompt_dir=str(prompts_dir))
        yield vault, prompts_dir


def test_delete_template_endpoint_success(test_vault_with_template: tuple[Vault, Path]) -> None:
    """Test successful template deletion via API endpoint"""
    vault, prompts_dir = test_vault_with_template
    
    # Override dependency
    app.dependency_overrides[get_vault] = lambda: vault
    
    try:
        client = TestClient(app)
        
        # Verify template exists
        response = client.get("/api/templates/test-template")
        assert response.status_code == 200
        
        # Delete the template
        response = client.delete("/api/templates/test-template")
        assert response.status_code == 204
        assert response.content == b''  # 204 No Content should have empty body
        
        # Verify template is gone
        response = client.get("/api/templates/test-template")
        assert response.status_code == 404
        
        # Verify template is not in list
        response = client.get("/api/templates")
        assert response.status_code == 200
        template_ids = response.json()
        assert "test-template" not in template_ids
        
        # Verify file is deleted
        assert not (prompts_dir / "test-template.yaml").exists()
        
    finally:
        app.dependency_overrides.clear()


def test_delete_template_endpoint_not_found(test_vault_with_template: tuple[Vault, Path]) -> None:
    """Test deleting non-existent template returns 404"""
    vault, _ = test_vault_with_template
    
    app.dependency_overrides[get_vault] = lambda: vault
    
    try:
        client = TestClient(app)
        
        # Attempt to delete non-existent template
        response = client.delete("/api/templates/nonexistent-template")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
    finally:
        app.dependency_overrides.clear()


def test_delete_template_endpoint_other_templates_unaffected(test_vault_with_template: tuple[Vault, Path]) -> None:
    """Test that deleting one template doesn't affect others"""
    vault, prompts_dir = test_vault_with_template
    
    app.dependency_overrides[get_vault] = lambda: vault
    
    try:
        client = TestClient(app)
        
        # Verify both templates exist
        response = client.get("/api/templates")
        assert response.status_code == 200
        template_ids = response.json()
        assert "test-template" in template_ids
        assert "another-template" in template_ids
        
        # Delete one template
        response = client.delete("/api/templates/test-template")
        assert response.status_code == 204
        
        # Verify the other template still exists
        response = client.get("/api/templates/another-template")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "another-template"
        
        # Verify file still exists
        assert (prompts_dir / "another-template.yaml").exists()
        
    finally:
        app.dependency_overrides.clear()


def test_delete_template_cache_invalidation_via_api(test_vault_with_template: tuple[Vault, Path]) -> None:
    """Test that API delete invalidates vault cache"""
    vault, _ = test_vault_with_template
    
    app.dependency_overrides[get_vault] = lambda: vault
    
    try:
        client = TestClient(app)
        
        # Load template into cache
        response = client.get("/api/templates/test-template")
        assert response.status_code == 200
        
        # Delete template
        response = client.delete("/api/templates/test-template")
        assert response.status_code == 204
        
        # Immediate GET should return 404 (cache invalidated)
        response = client.get("/api/templates/test-template")
        assert response.status_code == 404
        
    finally:
        app.dependency_overrides.clear()


def test_delete_then_recreate_template(test_vault_with_template: tuple[Vault, Path]) -> None:
    """Test that a template can be recreated after deletion"""
    vault, _ = test_vault_with_template
    
    app.dependency_overrides[get_vault] = lambda: vault
    
    try:
        client = TestClient(app)
        
        # Delete template
        response = client.delete("/api/templates/test-template")
        assert response.status_code == 204
        
        # Verify it's gone
        response = client.get("/api/templates/test-template")
        assert response.status_code == 404
        
        # Recreate with same ID
        new_template: dict[str, object] = {
            "id": "test-template",
            "version": "2.0.0",
            "description": "Recreated template",
            "template": "Welcome back {{ name }}",
            "inputs": {
                "name": {
                    "type": "string",
                    "required": True
                }
            },
            "metadata": {}
        }
        
        response = client.post("/api/templates", json=new_template)
        assert response.status_code == 200
        
        # Verify new template exists
        response = client.get("/api/templates/test-template")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["description"] == "Recreated template"
        
    finally:
        app.dependency_overrides.clear()


def test_delete_template_idempotency() -> None:
    """Test that deleting the same template twice returns appropriate responses"""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        
        template = prompts_dir / "test-template.yaml"
        template.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello'\n"
            "inputs: {}\n"
        )
        
        vault = Vault(prompt_dir=str(prompts_dir))
        app.dependency_overrides[get_vault] = lambda: vault
        
        try:
            client = TestClient(app)
            
            # First delete succeeds
            response = client.delete("/api/templates/test-template")
            assert response.status_code == 204
            
            # Second delete returns 404 (template already gone)
            response = client.delete("/api/templates/test-template")
            assert response.status_code == 404
            
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
