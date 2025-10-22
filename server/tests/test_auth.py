"""Comprehensive tests for authentication flows in Dakora API.

Tests cover:
- API key authentication via endpoints
- JWT token authentication via endpoints
- No-auth mode (development)
- Error handling and edge cases
- Protected endpoints with various auth methods
- Multi-tenancy with storage prefixes
"""

import tempfile
from pathlib import Path
from typing import Generator
import pytest
import jwt
from uuid import UUID
from fastapi.testclient import TestClient

from dakora_server.main import app
from dakora_server.auth import AuthContext, get_project_vault, validate_project_access
from dakora_server.core.vault import Vault
from dakora_server.core.prompt_manager import PromptManager
from dakora_server.core.database import create_db_engine
from dakora_server.api.project_prompts import get_prompt_manager


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_vault_with_template(test_project_id: str) -> Generator[tuple[Vault, Path], None, None]:
    """Create a test vault with a sample template"""
    from dakora_server.core.database import create_db_engine, get_connection, prompts_table
    from sqlalchemy import insert
    from datetime import datetime

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create project-scoped directory
        prompts_dir = base_dir / "projects" / test_project_id
        prompts_dir.mkdir(parents=True)

        # Create test template in project directory
        template = prompts_dir / "test-template.yaml"
        template.write_text(
            "id: test-template\n"
            "version: '1.0.0'\n"
            "description: 'Test template for auth'\n"
            "template: 'Hello {{ name }}'\n"
            "inputs:\n"
            "  name:\n"
            "    type: string\n"
            "    required: true\n"
        )

        vault = Vault(prompt_dir=str(base_dir))

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
                        "description": "Test template for auth",
                        "last_updated_at": datetime.utcnow(),
                    }
                )
            )
            conn.commit()

        yield vault, prompts_dir


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


# ============================================================================
# AuthContext Tests
# ============================================================================


class TestAuthContext:
    """Tests for AuthContext model"""

    def test_auth_context_creation(self):
        """Test creating an AuthContext"""
        ctx = AuthContext(user_id="user123", auth_method="jwt")
        assert ctx.user_id == "user123"
        assert ctx.project_id is None
        assert ctx.auth_method == "jwt"

    def test_auth_context_storage_prefix_user(self):
        """Test storage prefix for user-scoped context"""
        ctx = AuthContext(user_id="user123", auth_method="jwt")
        assert ctx.storage_prefix == "users/user123"

    def test_auth_context_storage_prefix_project(self):
        """Test storage prefix for project-scoped context"""
        ctx = AuthContext(
            user_id="user123",
            project_id="proj456",
            auth_method="api_key",
        )
        assert ctx.storage_prefix == "projects/proj456"

    def test_auth_context_with_api_key(self):
        """Test creating AuthContext with API key"""
        ctx = AuthContext(
            user_id="apikey_abc123",
            auth_method="api_key",
        )
        assert ctx.auth_method == "api_key"
        assert ctx.user_id == "apikey_abc123"

    def test_auth_context_with_all_fields(self):
        """Test creating AuthContext with all fields populated"""
        ctx = AuthContext(
            user_id="user456",
            project_id="proj789",
            auth_method="jwt",
        )
        assert ctx.user_id == "user456"
        assert ctx.project_id == "proj789"
        assert ctx.auth_method == "jwt"
        assert ctx.storage_prefix == "projects/proj789"


# ============================================================================
# Protected Endpoints Tests - API Key Auth
# ============================================================================


class TestProtectedEndpointsWithAPIKey:
    """Tests for protected endpoints with API key authentication"""

    def test_list_templates_with_api_key(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test listing templates with API key"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        # Create prompt manager with scoped vault
        def mock_prompt_manager():
            engine = create_db_engine()
            return PromptManager(scoped_vault.registry, engine, UUID(test_project_id))

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)
        app.dependency_overrides[get_prompt_manager] = mock_prompt_manager

        try:
            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"X-API-Key": "test-key-123"},
            )
            assert response.status_code == 200
            templates = response.json()
            assert "test-template" in templates
        finally:
            app.dependency_overrides.clear()

    def test_get_template_with_api_key(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test getting a specific template with API key"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.get(
                f"/api/projects/{test_project_id}/prompts/test-template",
                headers={"X-API-Key": "my-api-key"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-template"
            assert data["description"] == "Test template for auth"
        finally:
            app.dependency_overrides.clear()

    def test_create_template_with_api_key(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test creating a template with API key"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.post(
                f"/api/projects/{test_project_id}/prompts",
                headers={"X-API-Key": "api-key-create"},
                json={
                    "id": "new-template",
                    "version": "1.0.0",
                    "description": "New template",
                    "template": "Test {{ var }}",
                    "inputs": {"var": {"type": "string", "required": True}},
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "new-template"
        finally:
            app.dependency_overrides.clear()

    def test_delete_template_with_api_key(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test deleting a template with API key"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            # Verify template exists
            response = client.get(
                f"/api/projects/{test_project_id}/prompts/test-template",
                headers={"X-API-Key": "api-key"},
            )
            assert response.status_code == 200

            # Delete with API key
            response = client.delete(
                f"/api/projects/{test_project_id}/prompts/test-template",
                headers={"X-API-Key": "api-key-delete"},
            )
            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Protected Endpoints Tests - JWT Auth
# ============================================================================


class TestProtectedEndpointsWithJWT:
    """Tests for protected endpoints with JWT token authentication"""

    def test_list_templates_with_jwt(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test listing templates with JWT token"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            payload = {"sub": "user123", "email": "user@example.com"}
            token = jwt.encode(payload, "secret", algorithm="HS256")

            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            templates = response.json()
            assert "test-template" in templates
        finally:
            app.dependency_overrides.clear()

    def test_get_template_with_jwt(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test getting a template with JWT token"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            payload = {"sub": "user456", "org": "acme"}
            token = jwt.encode(payload, "secret", algorithm="HS256")

            response = client.get(
                f"/api/projects/{test_project_id}/prompts/test-template",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-template"
        finally:
            app.dependency_overrides.clear()

    def test_create_template_with_jwt(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test creating a template with JWT token"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            payload = {"sub": "user789", "role": "admin"}
            token = jwt.encode(payload, "secret", algorithm="HS256")

            response = client.post(
                f"/api/projects/{test_project_id}/prompts",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "id": "jwt-created-template",
                    "version": "1.0.0",
                    "description": "Created via JWT",
                    "template": "JWT {{ content }}",
                    "inputs": {"content": {"type": "string", "required": True}},
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "jwt-created-template"
        finally:
            app.dependency_overrides.clear()

    def test_jwt_with_project_id(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
    ):
        """Test JWT token with project_id claim for multi-tenancy"""

        vault, _ = test_vault_with_template
        app.dependency_overrides[get_project_vault] = lambda: vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            payload = {
                "sub": "user_proj",
                "project_id": "proj_abc123",
            }
            token = jwt.encode(payload, "secret", algorithm="HS256")

            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Protected Endpoints Tests - No Auth (Dev Mode)
# ============================================================================


class TestProtectedEndpointsNoAuth:
    """Tests for protected endpoints in no-auth mode"""

    def test_list_templates_no_auth(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test listing templates without authentication"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.get(f"/api/projects/{test_project_id}/prompts")
            assert response.status_code == 200
            templates = response.json()
            assert "test-template" in templates
        finally:
            app.dependency_overrides.clear()

    def test_get_template_no_auth(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test getting a template without authentication"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.get(f"/api/projects/{test_project_id}/prompts/test-template")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test-template"
        finally:
            app.dependency_overrides.clear()

    def test_create_template_no_auth(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test creating a template without authentication"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.post(
                f"/api/projects/{test_project_id}/prompts",
                json={
                    "id": "no-auth-template",
                    "version": "1.0.0",
                    "description": "No auth template",
                    "template": "Test",
                    "inputs": {},
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "no-auth-template"
        finally:
            app.dependency_overrides.clear()

    def test_delete_template_no_auth(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test deleting a template without authentication"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            response = client.delete(f"/api/projects/{test_project_id}/prompts/test-template")
            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Multi-Tenancy Tests
# ============================================================================


class TestMultiTenancy:
    """Tests for multi-tenancy with storage prefixes"""

    def test_user_storage_prefix(self):
        """Test that user-scoped vault has correct prefix"""
        auth_ctx = AuthContext(user_id="user123", auth_method="jwt")
        assert auth_ctx.storage_prefix == "users/user123"

    def test_project_storage_prefix(self):
        """Test that project-scoped vault has correct prefix"""
        auth_ctx = AuthContext(
            user_id="user123",
            project_id="proj456",
            auth_method="jwt",
        )
        assert auth_ctx.storage_prefix == "projects/proj456"

    def test_api_key_user_scope(self):
        """Test API key creates user-scoped context"""
        auth_ctx = AuthContext(
            user_id="apikey_abc123",
            auth_method="api_key",
        )
        # Should use user prefix since no project_id
        assert "apikey_abc123" in auth_ctx.storage_prefix
        assert auth_ctx.storage_prefix.startswith("users/")

    def test_api_key_with_project(self):
        """Test API key with project scope"""
        auth_ctx = AuthContext(
            user_id="apikey_abc123",
            project_id="proj789",
            auth_method="api_key",
        )
        # Should use project prefix
        assert auth_ctx.storage_prefix == "projects/proj789"

    def test_different_users_different_prefixes(self):
        """Test that different users get different storage prefixes"""
        ctx1 = AuthContext(user_id="user1", auth_method="jwt")
        ctx2 = AuthContext(user_id="user2", auth_method="jwt")

        assert ctx1.storage_prefix != ctx2.storage_prefix
        assert ctx1.storage_prefix == "users/user1"
        assert ctx2.storage_prefix == "users/user2"

    def test_same_user_different_projects(self):
        """Test same user with different projects"""
        ctx1 = AuthContext(user_id="user1", project_id="proj1", auth_method="jwt")
        ctx2 = AuthContext(user_id="user1", project_id="proj2", auth_method="jwt")

        assert ctx1.storage_prefix != ctx2.storage_prefix
        assert ctx1.storage_prefix == "projects/proj1"
        assert ctx2.storage_prefix == "projects/proj2"


# ============================================================================
# Auth Method Priority Tests
# ============================================================================


class TestAuthMethodPriority:
    """Tests for authentication method priority"""

    def test_api_key_priority_over_jwt(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
        scoped_vault_for_project,
    ):
        """Test that API key has priority over JWT token"""

        vault, _ = test_vault_with_template
        scoped_vault = scoped_vault_for_project(vault)

        app.dependency_overrides[get_project_vault] = lambda: scoped_vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            api_key = "priority-api-key"
            payload = {"sub": "user_from_jwt"}
            token = jwt.encode(payload, "secret", algorithm="HS256")

            # Send both API key and JWT - API key should win
            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={
                    "X-API-Key": api_key,
                    "Authorization": f"Bearer {token}",
                },
            )
            assert response.status_code == 200
            templates = response.json()
            assert "test-template" in templates
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in authentication"""

    def test_malformed_bearer_token(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
    ):
        """Test handling of malformed Bearer token"""

        vault, _ = test_vault_with_template
        app.dependency_overrides[get_project_vault] = lambda: vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            # Token is not valid JWT
            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"Authorization": "Bearer not-a-valid-jwt-token"},
            )
            # Should either handle gracefully or return error
            # Since we don't verify in no-auth mode, it should work or fail gracefully
            assert response.status_code in [200, 401]
        finally:
            app.dependency_overrides.clear()

    def test_wrong_auth_scheme(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
    ):
        """Test that non-Bearer schemes fall through to no-auth"""

        vault, _ = test_vault_with_template
        app.dependency_overrides[get_project_vault] = lambda: vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            token = jwt.encode({"sub": "user"}, "secret", algorithm="HS256")
            # Using Basic scheme instead of Bearer
            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"Authorization": f"Basic {token}"},
            )
            # Should fall through to no-auth mode and work
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_empty_api_key_header(
        self,
        client: TestClient,
        test_vault_with_template: tuple[Vault, Path],
        test_project_id: str,
    ):
        """Test handling of empty API key header"""

        vault, _ = test_vault_with_template
        app.dependency_overrides[get_project_vault] = lambda: vault
        app.dependency_overrides[validate_project_access] = lambda: UUID(test_project_id)

        try:
            # Empty API key still creates auth context
            response = client.get(
                f"/api/projects/{test_project_id}/prompts",
                headers={"X-API-Key": ""},
            )
            # Should handle and still work
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """Tests for health check endpoint accessibility"""

    def test_health_check_no_auth(self, client: TestClient):
        """Test that health check is accessible without auth"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_health_check_with_api_key(self, client: TestClient):
        """Test health check with API key"""
        response = client.get(
            "/api/health",
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 200

    def test_health_check_with_jwt(self, client: TestClient):
        """Test health check with JWT token"""
        payload = {"sub": "user"}
        token = jwt.encode(payload, "secret", algorithm="HS256")

        response = client.get(
            "/api/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
