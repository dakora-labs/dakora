"""Integration tests for template deletion API endpoint."""
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from uuid import UUID
from fastapi.testclient import TestClient

from dakora_server.main import app
from dakora_server.auth import get_project_vault, validate_project_access
from dakora_server.core.vault import Vault


@pytest.fixture
def test_vault_with_template(test_project_id: str) -> Generator[tuple[Vault, Path], None, None]:
    """Create a test vault with a sample template"""
    from dakora_server.core.database import create_db_engine, get_connection, prompts_table
    from sqlalchemy import insert, delete
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create project-scoped directory
        prompts_dir = base_dir / "projects" / test_project_id
        prompts_dir.mkdir(parents=True)

        # Create test templates in project directory
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

        vault = Vault(prompt_dir=str(base_dir))

        # Insert templates into database (delete first if exist to handle fixture reuse)
        engine = create_db_engine()
        with get_connection(engine) as conn:
            # Clean up any existing prompts first
            conn.execute(
                delete(prompts_table).where(
                    prompts_table.c.project_id == UUID(test_project_id)
                )
            )

            conn.execute(
                insert(prompts_table).values([
                    {
                        "project_id": UUID(test_project_id),
                        "prompt_id": "test-template",
                        "storage_path": f"projects/{test_project_id}/test-template.yaml",
                        "version": "1.0.0",
                        "description": "Test template for deletion",
                        "last_updated_at": datetime.utcnow(),
                    },
                    {
                        "project_id": UUID(test_project_id),
                        "prompt_id": "another-template",
                        "storage_path": f"projects/{test_project_id}/another-template.yaml",
                        "version": "1.0.0",
                        "description": "Another test template",
                        "last_updated_at": datetime.utcnow(),
                    },
                ])
            )
            conn.commit()

        yield vault, prompts_dir

        # Cleanup: Delete templates from database
        with get_connection(engine) as conn:
            conn.execute(
                delete(prompts_table).where(
                    prompts_table.c.project_id == UUID(test_project_id)
                )
            )
            conn.commit()

@pytest.mark.integration
def test_delete_template_endpoint_success(
    test_vault_with_template: tuple[Vault, Path],
    test_project_id: str,
) -> None:
    """Test successful template deletion via API endpoint"""
    base_vault, prompts_dir = test_vault_with_template

    # Create project-scoped vault (mimicking get_project_vault dependency)
    from typing import cast
    from dakora_server.core.registry import Registry

    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
    )
    vault = Vault(scoped_registry, logging_enabled=False)

    # Override dependencies
    app.dependency_overrides[get_project_vault] = lambda: vault
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    try:
        client = TestClient(app)

        # Verify template exists
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 200

        # Delete the template
        response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 204
        assert response.content == b''  # 204 No Content should have empty body

        # Verify template is gone
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 404

        # Verify template is not in list
        response = client.get(f"/api/projects/{test_project_id}/prompts")
        assert response.status_code == 200
        templates = response.json()
        template_ids = [t['id'] for t in templates]
        assert "test-template" not in template_ids

        # Verify file is deleted
        assert not (prompts_dir / "test-template.yaml").exists()

    finally:
        app.dependency_overrides.clear()

@pytest.mark.integration
def test_delete_template_endpoint_not_found(
    test_vault_with_template: tuple[Vault, Path],
    test_project_id: str,
) -> None:
    """Test deleting non-existent template returns 404"""
    base_vault, _ = test_vault_with_template

    # Create project-scoped vault
    from typing import cast
    from dakora_server.core.registry import Registry

    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
    )
    vault = Vault(scoped_registry, logging_enabled=False)

    app.dependency_overrides[get_project_vault] = lambda: vault
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    try:
        client = TestClient(app)

        # Attempt to delete non-existent template
        response = client.delete(f"/api/projects/{test_project_id}/prompts/nonexistent-template")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    finally:
        app.dependency_overrides.clear()

@pytest.mark.integration
def test_delete_template_endpoint_other_templates_unaffected(
    test_vault_with_template: tuple[Vault, Path],
    test_project_id: str,
) -> None:
    """Test that deleting one template doesn't affect others"""
    base_vault, prompts_dir = test_vault_with_template

    # Create project-scoped vault
    from typing import cast
    from dakora_server.core.registry import Registry

    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
    )
    vault = Vault(scoped_registry, logging_enabled=False)

    app.dependency_overrides[get_project_vault] = lambda: vault
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    try:
        client = TestClient(app)

        # Verify both templates exist
        response = client.get(f"/api/projects/{test_project_id}/prompts")
        assert response.status_code == 200
        templates = response.json()
        template_ids = [t['id'] for t in templates]
        assert "test-template" in template_ids
        assert "another-template" in template_ids

        # Delete one template
        response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 204

        # Verify the other template still exists
        response = client.get(f"/api/projects/{test_project_id}/prompts/another-template")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "another-template"

        # Verify file still exists
        assert (prompts_dir / "another-template.yaml").exists()

    finally:
        app.dependency_overrides.clear()

@pytest.mark.integration
def test_delete_template_cache_invalidation_via_api(
    test_vault_with_template: tuple[Vault, Path],
    test_project_id: str,
) -> None:
    """Test that API delete invalidates vault cache"""
    base_vault, _ = test_vault_with_template

    # Create project-scoped vault
    from typing import cast
    from dakora_server.core.registry import Registry

    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
    )
    vault = Vault(scoped_registry, logging_enabled=False)

    app.dependency_overrides[get_project_vault] = lambda: vault
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    try:
        client = TestClient(app)

        # Load template into cache
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 200

        # Delete template
        response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 204

        # Immediate GET should return 404 (cache invalidated)
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()

@pytest.mark.integration
def test_delete_then_recreate_template(
    test_vault_with_template: tuple[Vault, Path],
    test_project_id: str,
) -> None:
    """Test that a template can be recreated after deletion"""
    base_vault, _ = test_vault_with_template

    # Create project-scoped vault
    from typing import cast
    from dakora_server.core.registry import Registry

    scoped_registry = cast(
        Registry,
        base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
    )
    vault = Vault(scoped_registry, logging_enabled=False)

    app.dependency_overrides[get_project_vault] = lambda: vault
    app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

    try:
        client = TestClient(app)

        # Delete template
        response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
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

        response = client.post(f"/api/projects/{test_project_id}/prompts", json=new_template)
        assert response.status_code == 201

        # Verify new template exists
        response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["description"] == "Recreated template"

    finally:
        app.dependency_overrides.clear()

@pytest.mark.integration
def test_delete_template_idempotency(test_project_id: str) -> None:
    """Test that deleting the same template twice returns appropriate responses"""
    from dakora_server.core.database import create_db_engine, get_connection, prompts_table
    from sqlalchemy import insert
    from datetime import datetime
    from typing import cast
    from dakora_server.core.registry import Registry

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create project-scoped directory
        prompts_dir = base_dir / "projects" / test_project_id
        prompts_dir.mkdir(parents=True)

        template = prompts_dir / "test-template.yaml"
        template.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "template: 'Hello'\n"
            "inputs: {}\n"
        )

        base_vault = Vault(prompt_dir=str(base_dir))

        # Insert template into database
        engine = create_db_engine()
        with get_connection(engine) as conn:
            conn.execute(
                insert(prompts_table).values(
                    {
                        "project_id": UUID(test_project_id),
                        "prompt_id": "test-template",
                        "storage_path": f"projects/{test_project_id}/test-template.yaml",
                        "version": "1.0.0",
                        "description": "",
                        "last_updated_at": datetime.utcnow(),
                    }
                )
            )
            conn.commit()

        # Create project-scoped vault
        scoped_registry = cast(
            Registry,
            base_vault.registry.with_prefix(f"projects/{test_project_id}")  # type: ignore[attr-defined]
        )
        vault = Vault(scoped_registry, logging_enabled=False)

        app.dependency_overrides[get_project_vault] = lambda: vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            client = TestClient(app)

            # First delete succeeds
            response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
            assert response.status_code == 204

            # Second delete returns 404 (template already gone)
            response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
            assert response.status_code == 404

        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
