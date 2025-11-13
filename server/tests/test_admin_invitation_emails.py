"""Tests for admin invitation approval/rejection with email sending"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
from datetime import datetime, timezone

from dakora_server.main import app
from dakora_server.api.admin_invitations import get_email_service
from dakora_server.core.email_service import EmailService
from dakora_server.auth import require_platform_admin, get_current_user_id, AuthContext


@pytest.fixture(scope="module")
def admin_user_id(db_engine):
    """UUID for admin user - creates user in DB once per module"""
    from dakora_server.core.database import users_table, get_connection
    from sqlalchemy import select
    
    admin_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    
    # Check if admin user already exists, if not create it
    with get_connection(db_engine) as conn:
        existing = conn.execute(
            select(users_table.c.id).where(users_table.c.id == admin_id)
        ).fetchone()
        
        if not existing:
            conn.execute(
                users_table.insert().values(
                    id=admin_id,
                    clerk_user_id="admin_clerk_user",
                    email="admin@dakora.io",
                    name="Admin User"
                )
            )
            conn.commit()
    
    return admin_id


@pytest.fixture
def admin_auth_context(admin_user_id):
    """AuthContext for admin user with platform_role=admin"""
    return AuthContext(
        user_id=str(admin_user_id),
        project_id=None,
        auth_method="test",
        public_metadata={"platform_role": "admin"}
    )


@pytest.fixture
def admin_auth_headers(admin_auth_context, admin_user_id):
    """Override auth dependencies for admin tests"""
    async def mock_require_platform_admin():
        return admin_auth_context
    
    async def mock_get_current_user_id():
        return admin_user_id
    
    app.dependency_overrides[require_platform_admin] = mock_require_platform_admin
    app.dependency_overrides[get_current_user_id] = mock_get_current_user_id
    
    yield {"Authorization": "Bearer test_admin_token"}
    
    # Clean up (will be overridden again by email service mock, cleared at test end)


@pytest.fixture
def mock_clerk_api(monkeypatch):
    """Mock httpx.AsyncClient for Clerk API calls"""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json = Mock(return_value={"id": "inv_123", "email_address": "test@example.com"})
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    # Patch httpx.AsyncClient
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda: mock_client)
    
    return mock_client


class TestAdminApprovalWithEmail:
    """Test admin approval endpoint sends custom invitation email"""
    
    def test_approve_invitation_sends_custom_email(self, db_connection, admin_auth_headers, mock_clerk_api):
        """Test that approving an invitation sends a custom branded email"""
        # Mock settings.clerk_secret_key to avoid 503 error in CI
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = None
            
            # Create a mock email service
            mock_email_service = Mock(spec=EmailService)
            mock_email_service.send_email.return_value = True
            
            # Override the email service dependency
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            # Create test client AFTER setting up dependency overrides
            client = TestClient(app)
            
            try:
                # Insert a pending invitation request
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="john@example.com",
                        name="John Doe",
                        company="Example Corp",
                        use_case="Testing",
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                # Mock Clerk API response - need to add url to response
                mock_clerk_api.post.return_value.status_code = 201
                mock_clerk_api.post.return_value.json.return_value = {
                    "id": "inv_123456",
                    "email_address": "john@example.com",
                    "url": "https://clerk.example.com/invite/inv_123456"
                }
                
                # Approve the invitation
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["message"] == "Invitation approved and sent to john@example.com"
                assert data["clerk_invitation_id"] == "inv_123456"
                
                # Verify email was sent
                mock_email_service.send_email.assert_called_once()
                call_args = mock_email_service.send_email.call_args
                
                assert call_args.kwargs["to"] == ["john@example.com"]
                assert call_args.kwargs["subject"] == "You're Invited to Dakora Studio!"
                assert "John Doe" in call_args.kwargs["html_content"]
                
            finally:
                # Clean up dependency override
                client.close()
                app.dependency_overrides.clear()
    
    def test_approve_invitation_email_failure_doesnt_block(self, db_connection, admin_auth_headers, mock_clerk_api):
        """Test that email failure doesn't prevent invitation approval"""
        # Mock settings.clerk_secret_key to avoid 503 error in CI
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = None
            
            # Create a mock email service that fails
            mock_email_service = Mock(spec=EmailService)
            mock_email_service.send_email.return_value = False
            
            # Override the email service dependency
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            # Create test client AFTER setting up dependency overrides
            client = TestClient(app)
            
            try:
                # Insert a pending invitation request
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="jane@example.com",
                        name="Jane Smith",
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                # Mock Clerk API response with url
                mock_clerk_api.post.return_value.status_code = 201
                mock_clerk_api.post.return_value.json.return_value = {
                    "id": "inv_789",
                    "email_address": "jane@example.com",
                    "url": "https://clerk.example.com/invite/inv_789"
                }
                
                # Approve the invitation
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                # Should still succeed even though email failed
                assert response.status_code == 200
                
                # Verify database was updated
                from sqlalchemy import select
                result = db_connection.execute(
                    select(invitation_requests_table).where(
                        invitation_requests_table.c.id == invitation_id
                    )
                ).fetchone()
                
                assert result.status == "approved"
                assert result.clerk_invitation_id == "inv_789"
                
            finally:
                # Clean up dependency override
                client.close()
                app.dependency_overrides.clear()
    
    def test_approve_uses_email_prefix_when_name_missing(self, db_connection, admin_auth_headers, mock_clerk_api):
        """Test that approval email uses email prefix when name is missing"""
        # Mock settings.clerk_secret_key to avoid 503 error in CI
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = None
            
            # Create a mock email service
            mock_email_service = Mock(spec=EmailService)
            mock_email_service.send_email.return_value = True
            
            # Override the email service dependency
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            # Create test client AFTER setting up dependency overrides
            client = TestClient(app)
            
            try:
                # Insert a pending invitation request WITHOUT a name
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="testuser@example.com",
                        name=None,
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                # Mock Clerk API response with url
                mock_clerk_api.post.return_value.status_code = 201
                mock_clerk_api.post.return_value.json.return_value = {
                    "id": "inv_abc",
                    "email_address": "testuser@example.com",
                    "url": "https://clerk.example.com/invite/inv_abc"
                }
                
                # Approve the invitation
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                assert response.status_code == 200
                
                # Verify email was sent with email prefix as name
                mock_email_service.send_email.assert_called_once()
                call_args = mock_email_service.send_email.call_args
                assert "testuser" in call_args.kwargs["html_content"]
                
            finally:
                # Clean up dependency override
                client.close()
                app.dependency_overrides.clear()


class TestAdminRejectionWithEmail:
    """Test admin rejection endpoint sends rejection email"""
    
    def test_reject_invitation_sends_email(self, db_connection, admin_auth_headers):
        """Test that rejecting an invitation sends a polite rejection email"""
        # Create a mock email service
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_email.return_value = True
        
        # Override the email service dependency
        app.dependency_overrides[get_email_service] = lambda: mock_email_service
        
        # Create test client AFTER setting up dependency overrides
        client = TestClient(app)
        
        try:
            # Insert a pending invitation request
            from dakora_server.core.database import invitation_requests_table
            
            invitation_id = uuid4()
            db_connection.execute(
                invitation_requests_table.insert().values(
                    id=invitation_id,
                    email="reject@example.com",
                    name="Reject User",
                    status="pending",
                    requested_at=datetime.now(timezone.utc)
                )
            )
            db_connection.commit()
            
            # Reject the invitation
            response = client.post(
                "/api/admin/invitations/reject",
                json={
                    "invitation_id": str(invitation_id),
                    "reason": "Not a good fit at this time"
                },
                headers=admin_auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Invitation request rejected"
            
            # Verify email was sent
            mock_email_service.send_email.assert_called_once()
            call_args = mock_email_service.send_email.call_args
            
            assert call_args.kwargs["to"] == ["reject@example.com"]
            assert call_args.kwargs["subject"] == "Thank You for Your Interest in Dakora"
            assert "Reject User" in call_args.kwargs["html_content"]
            assert "thank you" in call_args.kwargs["html_content"].lower()
            
        finally:
            # Clean up dependency override
            client.close()
            app.dependency_overrides.clear()
    
    def test_reject_invitation_email_failure_doesnt_block(self, db_connection, admin_auth_headers):
        """Test that email failure doesn't prevent invitation rejection"""
        # Create a mock email service that fails
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_email.return_value = False
        
        # Override the email service dependency
        app.dependency_overrides[get_email_service] = lambda: mock_email_service
        
        # Create test client AFTER setting up dependency overrides
        client = TestClient(app)
        
        try:
            # Insert a pending invitation request
            from dakora_server.core.database import invitation_requests_table
            
            invitation_id = uuid4()
            db_connection.execute(
                invitation_requests_table.insert().values(
                    id=invitation_id,
                    email="failtest@example.com",
                    name="Fail Test",
                    status="pending",
                    requested_at=datetime.now(timezone.utc)
                )
            )
            db_connection.commit()
            
            # Reject the invitation
            response = client.post(
                "/api/admin/invitations/reject",
                json={"invitation_id": str(invitation_id)},
                headers=admin_auth_headers
            )
            
            # Should still succeed even though email failed
            assert response.status_code == 200
            
            # Verify database was updated
            from sqlalchemy import select
            result = db_connection.execute(
                select(invitation_requests_table).where(
                    invitation_requests_table.c.id == invitation_id
                )
            ).fetchone()
            
            assert result.status == "rejected"
            
        finally:
            # Clean up dependency override
            client.close()
            app.dependency_overrides.clear()
    
    def test_reject_uses_email_prefix_when_name_missing(self, db_connection, admin_auth_headers):
        """Test that rejection email uses email prefix when name is missing"""
        # Create a mock email service
        mock_email_service = Mock(spec=EmailService)
        mock_email_service.send_email.return_value = True
        
        # Override the email service dependency
        app.dependency_overrides[get_email_service] = lambda: mock_email_service
        
        # Create test client AFTER setting up dependency overrides
        client = TestClient(app)
        
        try:
            # Insert a pending invitation request WITHOUT a name
            from dakora_server.core.database import invitation_requests_table
            
            invitation_id = uuid4()
            db_connection.execute(
                invitation_requests_table.insert().values(
                    id=invitation_id,
                    email="noname@example.com",
                    name=None,
                    status="pending",
                    requested_at=datetime.now(timezone.utc)
                )
            )
            db_connection.commit()
            
            # Reject the invitation
            response = client.post(
                "/api/admin/invitations/reject",
                json={"invitation_id": str(invitation_id)},
                headers=admin_auth_headers
            )
            
            assert response.status_code == 200
            
            # Verify email was sent with email prefix as name
            mock_email_service.send_email.assert_called_once()
            call_args = mock_email_service.send_email.call_args
            assert "noname" in call_args.kwargs["html_content"]
            
        finally:
            # Clean up dependency override
            client.close()
            app.dependency_overrides.clear()
