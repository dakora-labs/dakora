"""Public invitation endpoint - no auth required"""

from fastapi import APIRouter, HTTPException, status, Request, Depends
from pydantic import BaseModel, EmailStr
import httpx
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
from typing import Any, Optional
from ..config import settings
from ..core.database import get_engine, get_connection, invitation_requests_table
from ..core.email_service import EmailService
from ..core.email_templates import render_confirmation_email, render_team_notification_email

router = APIRouter(prefix="/api/public", tags=["public"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


def get_email_service() -> EmailService:
    """Dependency to get email service instance"""
    return EmailService(api_key=settings.resend_api_key)


class InviteRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    company: str | None = None
    use_case: str | None = None


# Reusable user-facing messages
MSG_PENDING = "Your invite request is under review. We'll send your invitation within 24 hours!"
MSG_APPROVED = "You already have an approved invitation! Check your email inbox (and spam folder) for the invite link."
MSG_EXISTS = "This email is already registered. Please sign in."


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "data" in payload:
        data = payload.get("data")
        return data if isinstance(data, list) else []
    return payload if isinstance(payload, list) else []


async def _clerk_user_exists(email: str) -> bool:
    """Return True if Clerk has a user with the given email.
    
    Raises:
        HTTPException: 503 if Clerk API is unavailable or times out
    """
    if not settings.clerk_secret_key:
        return False
    email_lower = email.lower()
    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            lists: list[list] = []
            r1 = await client.get(
                "https://api.clerk.com/v1/users", headers=headers, params={"email_address": email}
            )
            lists.append(_as_list(r1.json()) if r1.status_code == 200 else [])
            r2 = await client.get(
                "https://api.clerk.com/v1/users", headers=headers, params=[("email_address[]", email)]
            )
            lists.append(_as_list(r2.json()) if r2.status_code == 200 else [])

            for users in lists:
                for u in users:
                    try:
                        emails = [
                            (e.get("email_address") or "").lower()
                            for e in (u.get("email_addresses") or [])
                            if isinstance(e, dict)
                        ]
                        if email_lower in emails:
                            return True
                    except Exception:
                        continue
    except httpx.TimeoutException:
        logger.error("Clerk API timeout during user lookup", extra={"email": email}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User verification service is temporarily unavailable. Please try again later."
        )
    except httpx.HTTPError as err:
        logger.error("Clerk API HTTP error during user lookup", extra={"email": email, "error": str(err)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User verification service is temporarily unavailable. Please try again later."
        )
    except Exception as err:
        logger.error("Unexpected error during Clerk user lookup", extra={"email": email, "error": str(err)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify user status. Please try again later."
        )
    return False


async def _clerk_invite_status(email: str) -> Optional[str]:
    """Return invitation status in Clerk for email: 'pending', 'accepted', or None.
    
    Raises:
        HTTPException: 503 if Clerk API is unavailable or times out
    """
    if not settings.clerk_secret_key:
        return None
    email_lower = email.lower()
    headers = {
        "Authorization": f"Bearer {settings.clerk_secret_key}",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            lists: list[list] = []
            r1 = await client.get(
                "https://api.clerk.com/v1/invitations", headers=headers, params={"email_address": email}
            )
            lists.append(_as_list(r1.json()) if r1.status_code == 200 else [])
            r2 = await client.get(
                "https://api.clerk.com/v1/invitations", headers=headers, params=[("email_address[]", email)]
            )
            lists.append(_as_list(r2.json()) if r2.status_code == 200 else [])

            found_pending = False
            found_accepted = False
            for invites in lists:
                for inv in invites:
                    try:
                        inv_email = (inv.get("email_address") or "").lower()
                        if inv_email != email_lower:
                            continue
                        status_val = (inv.get("status") or "").lower()
                        if status_val == "pending":
                            found_pending = True
                        elif status_val == "accepted":
                            found_accepted = True
                    except Exception:
                        continue
            if found_pending:
                return "pending"
            if found_accepted:
                return "accepted"
    except httpx.TimeoutException:
        logger.error("Clerk API timeout during invitation lookup", extra={"email": email}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invitation verification service is temporarily unavailable. Please try again later."
        )
    except httpx.HTTPError as err:
        logger.error("Clerk API HTTP error during invitation lookup", extra={"email": email, "error": str(err)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invitation verification service is temporarily unavailable. Please try again later."
        )
    except Exception as err:
        logger.error("Unexpected error during Clerk invitation lookup", extra={"email": email, "error": str(err)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify invitation status. Please try again later."
        )
    return None


@router.post("/invite-request", status_code=status.HTTP_200_OK)
@limiter.limit("3/15minutes")
async def request_invite(
    request: Request,
    invite_data: InviteRequest,
    email_service: EmailService = Depends(get_email_service)
):
    """
    Public endpoint to request invite. Saves request to database for admin approval.
    No authentication required.
    
    Rate limited to 3 requests per IP per 15 minutes to prevent spam.
    
    Args:
        request: FastAPI request object (required by slowapi for rate limiting)
        invite_data: Invitation request data (email, name, company, use_case)
        email_service: Email service dependency
        
    Returns:
        Dict with message confirming request was received
        
    Raises:
        HTTPException: 409 if email already has pending/approved request, 500 on error
    """
    engine = get_engine()
    
    try:
        # Clerk-first checks to prevent duplicate requests
        if await _clerk_user_exists(invite_data.email):
            return {"message": MSG_EXISTS, "status": "already_exists"}

        inv_status = await _clerk_invite_status(invite_data.email)
        if inv_status == "pending":
            return {"message": MSG_PENDING, "status": "already_pending"}
        if inv_status == "accepted":
            return {"message": MSG_APPROVED, "status": "already_approved"}

        # After Clerk, perform DB-level checks and save if allowed
        with get_connection(engine) as conn:
            # Check if email already has a pending or approved request locally
            existing = conn.execute(
                select(invitation_requests_table.c.status)
                .where(invitation_requests_table.c.email == invite_data.email)
            ).fetchone()
            
            if existing:
                status_value = existing[0]
                if status_value == "pending":
                    return {"message": MSG_PENDING, "status": "already_pending"}
                elif status_value == "approved":
                    return {"message": MSG_APPROVED, "status": "already_approved"}
                elif status_value == "rejected":
                    # Allow re-requesting if previously rejected
                    pass
            # Clerk checks were already performed above via helpers
            
            # Get request metadata
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Insert new request (with unique constraint protection)
            try:
                conn.execute(
                    insert(invitation_requests_table).values(
                        email=invite_data.email,
                        name=invite_data.name,
                        company=invite_data.company,
                        use_case=invite_data.use_case,
                        status="pending",
                        metadata={
                            "source": "landing_page_request",
                            "ip": client_ip,
                            "user_agent": user_agent,
                        }
                    )
                )
                conn.commit()
            except IntegrityError:
                # Race condition: another request just created a pending record
                logger.info(
                    "Duplicate pending invitation request detected (race condition)",
                    extra={"email": invite_data.email}
                )
                return {"message": MSG_PENDING, "status": "already_pending"}
        
        logger.info(
            "Invitation request saved",
            extra={
                "email": invite_data.email,
                "has_name": invite_data.name is not None,
                "has_company": invite_data.company is not None,
                "has_use_case": invite_data.use_case is not None
            }
        )
        
        # Send confirmation email (non-blocking - failure won't prevent request save)
        try:
            user_name = invite_data.name if invite_data.name else invite_data.email.split("@")[0]
            
            email_sent = email_service.send_email(
                to=[invite_data.email],
                subject="Your Dakora Studio Invitation Request",
                html_content=render_confirmation_email(
                    user_name=user_name,
                    user_email=invite_data.email
                )
            )
            
            if email_sent:
                logger.info(
                    "Confirmation email sent",
                    extra={"email": invite_data.email}
                )
            else:
                logger.warning(
                    "Confirmation email failed to send",
                    extra={"email": invite_data.email}
                )
        except Exception as email_error:
            logger.error(
                "Error sending confirmation email",
                extra={"email": invite_data.email, "error": str(email_error)},
                exc_info=True
            )
        
        # Send team notification email (non-blocking - failure won't prevent request save)
        # Can send to multiple recipients by passing a list
        try:
            team_email_sent = email_service.send_email(
                to=["mihailucianandrone@gmail.com","pistol.bogdan17@gmail.com"], 
                subject=f"New Invitation Request: {invite_data.email}",
                html_content=render_team_notification_email(
                    user_email=invite_data.email,
                    user_name=invite_data.name,
                    company=invite_data.company,
                    use_case=invite_data.use_case
                )
            )
            
            if team_email_sent:
                logger.info(
                    "Team notification email sent",
                    extra={"email": invite_data.email}
                )
            else:
                logger.warning(
                    "Team notification email failed to send",
                    extra={"email": invite_data.email}
                )
        except Exception as email_error:
            logger.error(
                "Error sending team notification email",
                extra={"email": invite_data.email, "error": str(email_error)},
                exc_info=True
            )
        
        return {
            "message": "Request received! We'll review and send your invitation within 24 hours. Check your email!"
        }
    
    except Exception as e:
        logger.error(
            "Failed to save invitation request",
            extra={"email": invite_data.email, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process invite request"
        )
