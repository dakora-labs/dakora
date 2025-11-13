"""Tests for invitation security

Tests for:
- Silent invitation failure handling with email fallback
- Race condition handling with unique constraint
- Clerk API error handling with proper exceptions
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4, UUID
from datetime import datetime, timezone
import httpx

from dakora_server.main import app
from dakora_server.api.admin_invitations import get_email_service
from dakora_server.core.email_service import EmailService
from dakora_server.auth import require_platform_admin, get_current_user_id, AuthContext
from sqlalchemy.exc import IntegrityError


@pytest.fixture(scope="module")
def admin_user_id(db_engine):
    """UUID for admin user - creates user in DB once per module"""
    from dakora_server.core.database import users_table, get_connection
    from sqlalchemy import select
    
    admin_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    
    with get_connection(db_engine) as conn:
        existing = conn.execute(
            select(users_table.c.id).where(users_table.c.id == admin_id)
        ).fetchone()
        
        if not existing:
            conn.execute(
                users_table.insert().values(
                    id=admin_id,
                    clerk_user_id="admin_clerk_user_security",
                    email="admin-security@dakora.io",
                    name="Admin Security Test"
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
        auth_method="jwt",
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
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_clerk_api_success(monkeypatch):
    """Mock httpx.AsyncClient for successful Clerk API calls"""
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json = Mock(return_value={
        "id": "inv_test123",
        "email_address": "test@example.com",
        "url": "https://clerk.example.com/invite/inv_test123"
    })
    
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    import httpx
    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=None: mock_client)
    
    return mock_client


class TestIssue1SilentInvitationFailure:
    """Tests for Issue #1: Silent Invitation Failure fix"""
    
    def test_clerk_email_used_when_resend_not_configured(self, db_connection, admin_auth_headers, mock_clerk_api_success):
        """Test that Clerk's email is used when Resend API key is not configured"""
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = None
            mock_settings.resend_api_key = None  # No Resend configured
            
            # Create a mock email service (shouldn't be called)
            mock_email_service = Mock(spec=EmailService)
            mock_email_service.send_email = Mock(return_value=False)
            
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            client = TestClient(app)
            
            try:
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="clerk-notify@example.com",
                        name="Clerk Notify Test",
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                # Verify that Clerk API was called with notify=True
                mock_clerk_api_success.post.return_value.status_code = 201
                mock_clerk_api_success.post.return_value.json.return_value = {
                    "id": "inv_clerk_notify",
                    "email_address": "clerk-notify@example.com",
                    "url": "https://clerk.example.com/invite/inv_clerk_notify"
                }
                
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                assert response.status_code == 200
                
                # Verify Clerk was called with notify=True (since no Resend)
                call_args = mock_clerk_api_success.post.call_args
                assert call_args is not None
                json_data = call_args[1]["json"]
                assert json_data["notify"] is True  # Should use Clerk email
                
                # Verify custom email service was NOT called
                mock_email_service.send_email.assert_not_called()
                
            finally:
                client.close()
                app.dependency_overrides.clear()
    
    def test_custom_email_sent_when_resend_configured(self, db_connection, admin_auth_headers, mock_clerk_api_success):
        """Test that custom email is sent when Resend is configured"""
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings:
            mock_settings.clerk_secret_key = "test_clerk_secret_key"
            mock_settings.invite_redirect_url = None
            mock_settings.resend_api_key = "re_test_key"  # Resend IS configured
            
            mock_email_service = Mock(spec=EmailService)
            mock_email_service.send_email = Mock(return_value=True)
            
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            client = TestClient(app)
            
            try:
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="custom-email@example.com",
                        name="Custom Email Test",
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                mock_clerk_api_success.post.return_value.status_code = 201
                mock_clerk_api_success.post.return_value.json.return_value = {
                    "id": "inv_custom_email",
                    "email_address": "custom-email@example.com",
                    "url": "https://clerk.example.com/invite/inv_custom_email"
                }
                
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                assert response.status_code == 200
                
                # Verify Clerk was called with notify=False (we send custom email)
                call_args = mock_clerk_api_success.post.call_args
                assert call_args is not None
                json_data = call_args[1]["json"]
                assert json_data["notify"] is False
                
                # Verify custom email WAS sent
                mock_email_service.send_email.assert_called_once()
                
            finally:
                client.close()
                app.dependency_overrides.clear()


class TestIssue2RaceConditionHandling:
    """Tests for Issue #2: Duplicate prevention with unique constraint"""
    
    def test_race_condition_caught_by_unique_constraint(self, db_connection):
        """Test that concurrent requests are prevented by unique constraint"""
        from dakora_server.core.database import invitation_requests_table
        from sqlalchemy import insert
        
        # First request succeeds
        invitation_id_1 = uuid4()
        db_connection.execute(
            insert(invitation_requests_table).values(
                id=invitation_id_1,
                email="race-test@example.com",
                name="Race Test",
                status="pending",
                requested_at=datetime.now(timezone.utc)
            )
        )
        db_connection.commit()
        
        # Second request with same email+pending status should fail
        invitation_id_2 = uuid4()
        with pytest.raises(IntegrityError):
            db_connection.execute(
                insert(invitation_requests_table).values(
                    id=invitation_id_2,
                    email="race-test@example.com",  # Same email
                    name="Race Test 2",
                    status="pending",  # Same status
                    requested_at=datetime.now(timezone.utc)
                )
            )
            db_connection.commit()
    
    def test_multiple_statuses_allowed_for_same_email(self, db_connection):
        """Test that same email can have multiple non-pending requests"""
        from dakora_server.core.database import invitation_requests_table
        from sqlalchemy import insert, update, select
        
        # First: pending request
        result = db_connection.execute(
            insert(invitation_requests_table).values(
                email="multi-status@example.com",
                name="Multi Status",
                status="pending",
                requested_at=datetime.now(timezone.utc)
            ).returning(invitation_requests_table.c.id)
        )
        first_id = result.fetchone()[0]
        db_connection.commit()
        
        # Mark first as approved (changes status from pending)
        db_connection.execute(
            update(invitation_requests_table)
            .where(invitation_requests_table.c.id == first_id)
            .values(status="approved", reviewed_at=datetime.now(timezone.utc))
        )
        db_connection.commit()
        
        # Verify first is no longer pending
        check = db_connection.execute(
            select(invitation_requests_table.c.status)
            .where(invitation_requests_table.c.id == first_id)
        ).fetchone()
        assert check[0] == "approved", "First invitation should be approved"
        
        # Now a new pending request should work (previous is approved)
        result2 = db_connection.execute(
            insert(invitation_requests_table).values(
                email="multi-status@example.com",
                name="Multi Status 2",
                status="pending",
                requested_at=datetime.now(timezone.utc)
            ).returning(invitation_requests_table.c.id)
        )
        second_id = result2.fetchone()[0]
        db_connection.commit()
        
        # Verify both exist with different IDs
        assert first_id != second_id, "Should have two different invitations"


class TestIssue3ClerkAPIErrorHandling:
    """Tests for Issue #3: Clerk API error handling"""
    
    def test_clerk_timeout_returns_503(self):
        """Test that Clerk API timeout returns 503"""
        from dakora_server.api.invitations import _clerk_user_exists
        
        with patch("dakora_server.api.invitations.settings") as mock_settings, \
             patch("dakora_server.api.invitations.httpx.AsyncClient") as mock_client_class:
            
            mock_settings.clerk_secret_key = "test_key"
            
            # Mock timeout exception
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            with pytest.raises(Exception) as exc_info:
                import asyncio
                asyncio.run(_clerk_user_exists("test@example.com"))
            
            # Should raise HTTPException with 503
            assert "503" in str(exc_info.value) or "unavailable" in str(exc_info.value).lower()
    
    def test_clerk_http_error_returns_503(self):
        """Test that Clerk API HTTP error returns 503"""
        from dakora_server.api.invitations import _clerk_invite_status
        
        with patch("dakora_server.api.invitations.settings") as mock_settings, \
             patch("dakora_server.api.invitations.httpx.AsyncClient") as mock_client_class:
            
            mock_settings.clerk_secret_key = "test_key"
            
            # Mock HTTP error
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("HTTP Error"))
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            with pytest.raises(Exception) as exc_info:
                import asyncio
                asyncio.run(_clerk_invite_status("test@example.com"))
            
            # Should raise HTTPException with 503
            assert "503" in str(exc_info.value) or "unavailable" in str(exc_info.value).lower()


class TestApprovalFlowBehavior:
    """Tests for overall approval flow behavior after fixes"""
    
    def test_approval_without_custom_email_still_succeeds(self, db_connection, admin_auth_headers):
        """Test that approval succeeds even without custom email service"""
        with patch("dakora_server.api.admin_invitations.settings") as mock_settings, \
             patch("dakora_server.api.admin_invitations.httpx.AsyncClient") as mock_client_class:
            
            mock_settings.clerk_secret_key = "test_key"
            mock_settings.invite_redirect_url = None
            mock_settings.resend_api_key = None  # No custom email
            
            # Mock Clerk API success
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json = Mock(return_value={
                "id": "inv_no_custom_email",
                "email_address": "no-custom@example.com",
                "url": "https://clerk.example.com/invite/inv_no_custom_email"
            })
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client
            
            mock_email_service = Mock(spec=EmailService)
            app.dependency_overrides[get_email_service] = lambda: mock_email_service
            
            client = TestClient(app)
            
            try:
                from dakora_server.core.database import invitation_requests_table
                
                invitation_id = uuid4()
                db_connection.execute(
                    invitation_requests_table.insert().values(
                        id=invitation_id,
                        email="no-custom@example.com",
                        name="No Custom Email",
                        status="pending",
                        requested_at=datetime.now(timezone.utc)
                    )
                )
                db_connection.commit()
                
                response = client.post(
                    "/api/admin/invitations/approve",
                    json={"invitation_id": str(invitation_id)},
                    headers=admin_auth_headers
                )
                
                # Should succeed
                assert response.status_code == 200
                
                # Verify invitation was marked as approved
                from sqlalchemy import select
                result = db_connection.execute(
                    select(invitation_requests_table).where(
                        invitation_requests_table.c.id == invitation_id
                    )
                ).fetchone()
                
                assert result.status == "approved"
                assert result.clerk_invitation_id is not None
                
            finally:
                client.close()
                app.dependency_overrides.clear()
