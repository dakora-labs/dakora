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
        # Mock both Clerk user and invitation lookups to return empty
        with patch("dakora_server.api.invitations._clerk_user_exists") as mock_user_exists, \
             patch("dakora_server.api.invitations._clerk_invite_status") as mock_invite_status:
            
            mock_user_exists.return_value = False
            mock_invite_status.return_value = None

            response = client.post(
                "/api/public/invite-request",
                json={
                    "email": "unique_test_1@example.com",
                    "name": "Test User",
                    "company": "Test Corp",
                    "use_case": "Testing the platform",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            # Should receive confirmation message for new request
            assert ("request received" in data["message"].lower() or 
                    "under review" in data["message"].lower())

    def test_invite_request_minimal_data(self, client):
        """Test invitation with only email (minimal required data)."""
        with patch("dakora_server.api.invitations._clerk_user_exists") as mock_user_exists, \
             patch("dakora_server.api.invitations._clerk_invite_status") as mock_invite_status:
            
            mock_user_exists.return_value = False
            mock_invite_status.return_value = None

            response = client.post(
                "/api/public/invite-request",
                json={"email": "unique_minimal_2@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            # Should receive confirmation message
            assert ("request received" in data["message"].lower() or 
                    "under review" in data["message"].lower())

    def test_invite_request_invalid_email(self, client):
        """Test invitation with invalid email format."""
        response = client.post(
            "/api/public/invite-request",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422  # Validation error

    def test_invite_request_duplicate_invitation(self, client):
        """Test handling of duplicate invitation (Clerk has pending invitation)."""
        with patch("dakora_server.api.invitations._clerk_user_exists") as mock_user_exists, \
             patch("dakora_server.api.invitations._clerk_invite_status") as mock_invite_status:
            
            mock_user_exists.return_value = False
            mock_invite_status.return_value = "pending"  # Simulate pending invitation

            response = client.post(
                "/api/public/invite-request",
                json={"email": "duplicate@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "already_pending"
            assert "under review" in data["message"].lower()
