"""Email service using Resend API"""

import logging
from typing import Optional

try:
    import resend
except ImportError:
    resend = None

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Resend API"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize email service with Resend API key
        
        Args:
            api_key: Resend API key (optional, will disable sending if None)
        """
        self.api_key = api_key
        self.from_email = "Dakora Team <team@dakora.io>"
        
        if api_key and resend:
            resend.api_key = api_key
        elif api_key and not resend:
            logger.warning("Resend package not installed, emails will not be sent")
        elif not api_key:
            logger.info("Email service initialized without API key, emails will not be sent")

    def send_email(
        self,
        to: list[str],
        subject: str,
        html_content: str,
    ) -> bool:
        """Send an email via Resend API
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            html_content: HTML content of the email
            
        Returns:
            True if email sent successfully, False otherwise
        """
        to_list = to
        
        if not self.api_key:
            logger.warning(
                "Email send skipped (no API key configured)",
                extra={"to": to_list, "subject": subject}
            )
            return False
            
        if not resend:
            logger.error(
                "Cannot send email: resend package not installed",
                extra={"to": to_list, "subject": subject}
            )
            return False

        try:
            params = {
                "from": self.from_email,
                "to": to_list,
                "subject": subject,
                "html": html_content,
            }
            
            result = resend.Emails.send(params)
            logger.info(
                "Email sent successfully",
                extra={"to": to_list, "subject": subject, "email_id": result.get("id")}
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send email",
                extra={"to": to_list, "subject": subject, "error": str(e)},
                exc_info=True
            )
            return False
