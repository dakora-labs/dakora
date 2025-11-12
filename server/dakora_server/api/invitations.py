"""Public invitation endpoint - no auth required"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
import httpx
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..config import settings

router = APIRouter(prefix="/api/public", tags=["public"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


class InviteRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    company: str | None = None
    use_case: str | None = None


@router.post("/invite-request", status_code=status.HTTP_200_OK)
@limiter.limit("3/15minutes")
async def request_invite(request: Request, invite_data: InviteRequest):
    """
    Public endpoint to request invite. Automatically sends Clerk invitation email.
    No authentication required.
    
    Rate limited to 3 requests per IP per 15 minutes to prevent spam.
    
    Args:
        request: FastAPI request object (required by slowapi for rate limiting)
        invite_data: Invitation request data (email, name, company, use_case)
        
    Returns:
        Dict with message and optional status field
        
    Raises:
        HTTPException: 503 if Clerk not configured, 504 on timeout, 500 on error
    """
    if not settings.clerk_secret_key:
        logger.error(
            "Invitation service not configured - CLERK_SECRET_KEY missing",
            extra={"email": invite_data.email}
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invitation service not configured"
        )

    # Determine redirect URL
    # If not specified, Clerk uses the default Account Portal sign-up page
    # which automatically handles the invitation flow
    redirect_url = settings.invite_redirect_url if settings.invite_redirect_url else None

    try:
        # Call Clerk API to create invitation
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.clerk.com/v1/invitations",
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "email_address": invite_data.email,
                    **({"redirect_url": redirect_url} if redirect_url else {}),
                    "public_metadata": {
                        "name": invite_data.name,
                        "company": invite_data.company,
                        "use_case": invite_data.use_case,
                        "source": "landing_page_request",
                    }
                },
                timeout=10.0
            )
            
            if response.status_code == 400:
                # Check if it's a duplicate invitation error
                response_data = response.json()
                errors = response_data.get("errors", [])
                if errors and errors[0].get("code") == "duplicate_record":
                    logger.info(
                        "Duplicate invitation attempt",
                        extra={"email": invite_data.email}
                    )
                    return {
                        "message": "You already have a pending invitation! Please check your email inbox (and spam folder) for the invite link. If you can't find it, contact support.",
                        "status": "already_invited"
                    }
            
            if response.status_code == 422:
                # User already exists or other validation error
                logger.info(
                    "User already exists",
                    extra={"email": invite_data.email}
                )
                return {
                    "message": "This email is already registered. Please sign in.",
                    "status": "already_exists"
                }
            
            if response.status_code not in [200, 201]:
                logger.error(
                    "Clerk API error",
                    extra={
                        "status_code": response.status_code,
                        "response_text": response.text[:500],  # Limit log size
                        "email": invite_data.email
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send invitation"
                )
        
        logger.info(
            "Invitation sent successfully",
            extra={
                "email": invite_data.email,
                "has_name": invite_data.name is not None,
                "has_company": invite_data.company is not None,
                "has_use_case": invite_data.use_case is not None
            }
        )
        return {
            "message": "Invitation sent! Check your email for your exclusive access link."
        }
    
    except httpx.TimeoutException:
        logger.error(
            "Clerk API timeout",
            extra={"email": invite_data.email},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Invitation service timed out"
        )
    except Exception as e:
        logger.error(
            "Failed to create invitation",
            extra={"email": invite_data.email, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process invite request"
        )
