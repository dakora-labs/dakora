"""Core integration tests for public invitation API endpoint.

These tests validate the essential functionality of the invitation endpoint.
Rate limiting tests are excluded due to TestClient state persistence issues.
Rate limiting is verified manually (3 requests per 15 minutes per IP).
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from dakora_server.main import create_app


@pytest.mark.integration
class TestInvitationsAPICore:
    """Core integration tests for invitation endpoint functionality."""

    @pytest.fixture
    def app(self):
        """Create app instance with mocked settings."""
        with patch("dakora_server.api.invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = "http://localhost:5173/sign-up"
            
            app = create_app()
            yield app
            app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, app):
        """Test client without auth requirements."""
        return TestClient(app)

    def test_invite_request_success(self, client):
        """Test successful invitation request with full data."""
        with patch("dakora_server.api.invitations.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "inv_test123"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            response = client.post(
                "/api/public/invite-request",
                json={
                    "email": "test@example.com",
                    "name": "Test User",
                    "company": "Test Corp",
                    "use_case": "Testing the platform",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "invitation sent" in data["message"].lower()

            # Verify Clerk API was called with correct data
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            
            assert call_args[0][0] == "https://api.clerk.com/v1/invitations"
            
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")
            
            json_data = call_args[1]["json"]
            assert json_data["email_address"] == "test@example.com"
            assert json_data["public_metadata"]["name"] == "Test User"
            assert json_data["public_metadata"]["company"] == "Test Corp"
            assert json_data["public_metadata"]["use_case"] == "Testing the platform"
            assert json_data["public_metadata"]["source"] == "landing_page_request"

    def test_invite_request_minimal_data(self, client):
        """Test invitation with only email (minimal required data)."""
        with patch("dakora_server.api.invitations.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            response = client.post(
                "/api/public/invite-request",
                json={"email": "minimal@example.com"},
            )

            assert response.status_code == 200
            
            # Verify metadata only includes source for minimal request
            call_args = mock_client_instance.post.call_args
            json_data = call_args[1]["json"]
            metadata = json_data["public_metadata"]
            assert metadata["source"] == "landing_page_request"
            assert "name" not in metadata or metadata.get("name") is None

    def test_invite_request_invalid_email(self, client):
        """Test invitation with invalid email format."""
        response = client.post(
            "/api/public/invite-request",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422  # Validation error

    def test_invite_request_duplicate_invitation(self, client):
        """Test handling of duplicate invitation (Clerk returns 400)."""
        with patch("dakora_server.api.invitations.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": [{"code": "duplicate_record", "message": "Invitation already exists"}]
            }
            
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            response = client.post(
                "/api/public/invite-request",
                json={"email": "duplicate@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_invited"
            assert "already have a pending invitation" in data["message"].lower()
