"""Tests for email service"""

from unittest.mock import patch
from dakora_server.core.email_service import EmailService
from dakora_server.core.email_templates import (
    render_confirmation_email,
    render_invitation_email,
    render_rejection_email,
)


class TestEmailService:
    """Tests for EmailService class"""

    def test_email_service_initialization(self):
        """Verify service initializes with API key"""
        service = EmailService(api_key="test_key_123")
        assert service.api_key == "test_key_123"
        assert service.from_email == "Dakora Team <team@dakora.io>"

    def test_email_service_initialization_no_key(self):
        """Verify service handles missing API key"""
        service = EmailService(api_key=None)
        assert service.api_key is None

    @patch("dakora_server.core.email_service.resend.Emails.send")
    def test_send_email_success(self, mock_send):
        """Verify email sends successfully with correct structure (single recipient)"""
        mock_send.return_value = {"id": "email_123"}
        
        service = EmailService(api_key="test_key")
        result = service.send_email(
            to=["user@example.com"],
            subject="Test Subject",
            html_content="<h1>Test</h1>",
        )
        
        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["from"] == "Dakora Team <team@dakora.io>"
        assert call_args["to"] == ["user@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<h1>Test</h1>"

    @patch("dakora_server.core.email_service.resend.Emails.send")
    def test_send_email_success_list_input(self, mock_send):
        """Verify email sends successfully with list of recipients"""
        mock_send.return_value = {"id": "email_456"}
        
        service = EmailService(api_key="test_key")
        result = service.send_email(
            to=["user1@example.com", "user2@example.com"],
            subject="Test Subject",
            html_content="<h1>Test</h1>",
        )
        
        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["from"] == "Dakora Team <team@dakora.io>"
        assert call_args["to"] == ["user1@example.com", "user2@example.com"]
        assert call_args["subject"] == "Test Subject"
        assert call_args["html"] == "<h1>Test</h1>"

    @patch("dakora_server.core.email_service.resend.Emails.send")
    def test_send_email_failure(self, mock_send):
        """Verify email failure is handled gracefully"""
        mock_send.side_effect = Exception("API Error")
        
        service = EmailService(api_key="test_key")
        result = service.send_email(
            to=["user@example.com"],
            subject="Test",
            html_content="<h1>Test</h1>",
        )
        
        assert result is False

    def test_send_email_no_api_key(self):
        """Verify sending without API key returns False"""
        service = EmailService(api_key=None)
        result = service.send_email(
            to=["user@example.com"],
            subject="Test",
            html_content="<h1>Test</h1>",
        )
        assert result is False


class TestEmailTemplates:
    """Tests for email template rendering"""

    def test_confirmation_email_rendering(self):
        """Verify confirmation email template renders with correct variables"""
        html = render_confirmation_email(
            user_name="John Doe",
            user_email="john@example.com",
        )
        
        assert "John Doe" in html
        assert "john@example.com" in html
        assert "24 hours" in html.lower() or "24-hour" in html.lower()
        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "support@dakora.io" in html.lower()

    def test_invitation_email_rendering(self):
        """Verify invitation email template renders with invite link"""
        html = render_invitation_email(
            user_name="Jane Smith",
            invite_url="https://dakora.io/accept?token=abc123",
        )
        
        assert "Jane Smith" in html
        assert "https://dakora.io/accept?token=abc123" in html
        assert "<!DOCTYPE html>" in html or "<html" in html
        assert "accept" in html.lower() or "join" in html.lower()

    def test_rejection_email_rendering(self):
        """Verify rejection email template is polite and professional"""
        html = render_rejection_email(user_name="Bob Johnson")
        
        assert "Bob Johnson" in html
        assert "<!DOCTYPE html>" in html or "<html" in html
        # Should be polite and encourage future application
        assert any(word in html.lower() for word in ["thank", "appreciate", "future", "again"])
