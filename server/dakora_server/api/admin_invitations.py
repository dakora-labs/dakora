"""Admin endpoints for managing invitation requests"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime, timezone
from uuid import UUID
import httpx
import logging
from sqlalchemy import select, update, desc

from ..auth import AuthContext, require_platform_admin, get_current_user_id
from ..config import settings
from ..core.database import get_engine, get_connection, invitation_requests_table
from ..core.email_service import EmailService
from ..core.email_templates import render_invitation_email, render_rejection_email

router = APIRouter(prefix="/api/admin/invitations", tags=["admin"])
logger = logging.getLogger(__name__)


def get_email_service() -> EmailService:
    """Dependency to get email service instance"""
    return EmailService(api_key=settings.resend_api_key)


class InvitationRequestResponse(BaseModel):
    """Invitation request data for admin view"""
    id: str
    email: str
    name: Optional[str]
    company: Optional[str]
    use_case: Optional[str]
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    rejection_reason: Optional[str]
    clerk_invitation_id: Optional[str]
    metadata: Optional[dict[str, Any]]


class InvitationListResponse(BaseModel):
    """List of invitation requests"""
    total: int
    pending: int
    approved: int
    rejected: int
    requests: list[InvitationRequestResponse]


class ApproveRequest(BaseModel):
    """Request to approve an invitation"""
    invitation_id: str


class RejectRequest(BaseModel):
    """Request to reject an invitation"""
    invitation_id: str
    reason: Optional[str] = None


@router.get("", response_model=InvitationListResponse)
async def list_invitations(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    _: AuthContext = Depends(require_platform_admin),
):
    """
    List all invitation requests with optional filtering.
    
    Requires platform admin role in Clerk public_metadata.
    
    Args:
        status_filter: Filter by status (pending, approved, rejected)
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of invitation requests with counts
    """
    from sqlalchemy import func
    
    engine = get_engine()
    
    with get_connection(engine) as conn:
        # Get counts by status
        counts_query = select(
            invitation_requests_table.c.status,
            func.count().label("count")
        ).group_by(invitation_requests_table.c.status)
        
        counts_result = conn.execute(counts_query).fetchall()
        counts = {row[0]: row[1] for row in counts_result}
        
        # Build main query
        query = select(invitation_requests_table).order_by(
            desc(invitation_requests_table.c.requested_at)
        )
        
        if status_filter:
            query = query.where(invitation_requests_table.c.status == status_filter)
        
        query = query.limit(limit).offset(offset)
        
        results = conn.execute(query).fetchall()
        
        requests = [
            InvitationRequestResponse(
                id=str(row.id),
                email=row.email,
                name=row.name,
                company=row.company,
                use_case=row.use_case,
                status=row.status,
                requested_at=row.requested_at,
                reviewed_at=row.reviewed_at,
                reviewed_by=str(row.reviewed_by) if row.reviewed_by else None,
                rejection_reason=row.rejection_reason,
                clerk_invitation_id=row.clerk_invitation_id,
                metadata=row.metadata,
            )
            for row in results
        ]
        
        # Get total count
        total_query = select(func.count()).select_from(invitation_requests_table)
        if status_filter:
            total_query = total_query.where(invitation_requests_table.c.status == status_filter)
        total = conn.execute(total_query).scalar()
        
        return InvitationListResponse(
            total=total or 0,
            pending=counts.get("pending", 0),
            approved=counts.get("approved", 0),
            rejected=counts.get("rejected", 0),
            requests=requests,
        )


@router.post("/approve")
async def approve_invitation(
    approve_req: ApproveRequest,
    auth_ctx: AuthContext = Depends(require_platform_admin),
    admin_user_id: UUID = Depends(get_current_user_id),
    email_service: EmailService = Depends(get_email_service),
):
    """
    Approve an invitation request and send Clerk invitation.
    
    Requires platform admin role in Clerk public_metadata.
    
    Args:
        approve_req: Approval request with invitation_id
        auth_ctx: Admin user auth context
        admin_user_id: Admin user database ID
        
    Returns:
        Success message with invitation details
        
    Raises:
        HTTPException: 404 if invitation not found, 400 if already processed, 500 on error
    """
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk not configured for sending invitations"
        )
    
    engine = get_engine()
    invitation_id = UUID(approve_req.invitation_id)
    
    with get_connection(engine) as conn:
        # Get the invitation request
        result = conn.execute(
            select(invitation_requests_table).where(
                invitation_requests_table.c.id == invitation_id
            )
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invitation request not found")
        
        if result.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Invitation already {result.status}"
            )
        
        # Determine redirect URL
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
                        "email_address": result.email,
                        # Match email template text (7 days) vs Clerk default (30)
                        "expires_in_days": 7,
                        "notify": False,
                        # Keep Clerk notification default (true) unless you prefer only branded emails
                        # Set "notify": False to avoid sending duplicate emails
                        **({"redirect_url": redirect_url} if redirect_url else {}),
                        "public_metadata": {
                            "name": result.name,
                            "company": result.company,
                            "use_case": result.use_case,
                            "source": "landing_page_request",
                        }
                    },
                    timeout=10.0
                )
                
                if response.status_code not in [200, 201]:
                    error_detail = response.text[:500]
                    logger.error(
                        "Clerk API error during approval",
                        extra={
                            "status_code": response.status_code,
                            "response": error_detail,
                            "email": result.email
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to send Clerk invitation: {error_detail}"
                    )
                
                clerk_data = response.json()
                clerk_invitation_id = clerk_data.get("id")
                clerk_invitation_url = clerk_data.get("url")
        
        except httpx.TimeoutException:
            logger.error("Clerk API timeout during approval", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Clerk invitation service timed out"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calling Clerk API: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send invitation"
            )
        
        # Update request status
        conn.execute(
            update(invitation_requests_table)
            .where(invitation_requests_table.c.id == invitation_id)
            .values(
                status="approved",
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=admin_user_id,
                clerk_invitation_id=clerk_invitation_id,
            )
        )
        conn.commit()
        
        logger.info(
            "Invitation approved and sent",
            extra={
                "invitation_id": str(invitation_id),
                "email": result.email,
                "approved_by": str(admin_user_id),
                "clerk_invitation_id": clerk_invitation_id
            }
        )
        
        # Send custom branded invitation email
        try:
            user_name = result.name if result.name else result.email.split("@")[0]
            # Prefer the URL provided by Clerk API response
            invite_url = clerk_invitation_url
            if not invite_url:
                logger.warning(
                    "Clerk invitation response missing URL; skipping custom email",
                    extra={
                        "invitation_id": str(invitation_id),
                        "email": result.email,
                    },
                )
                invite_url = None

            email_sent = False
            if invite_url:
                email_html = render_invitation_email(user_name, invite_url)
                email_sent = email_service.send_email(
                    to=result.email,
                    subject="You're Invited to Dakora Studio!",
                    html_content=email_html,
                )

            if email_sent:
                logger.info(f"Custom invitation email sent to {result.email}")
            else:
                logger.warning(f"Failed to send custom invitation email to {result.email}")
        except Exception as e:
            logger.error(f"Error sending custom invitation email: {e}", exc_info=True)
        
        return {
            "message": f"Invitation approved and sent to {result.email}",
            "invitation_id": str(invitation_id),
            "clerk_invitation_id": clerk_invitation_id
        }


@router.post("/reject")
async def reject_invitation(
    reject_req: RejectRequest,
    _: AuthContext = Depends(require_platform_admin),
    admin_user_id: UUID = Depends(get_current_user_id),
    email_service: EmailService = Depends(get_email_service),
):
    """
    Reject an invitation request.
    
    Requires platform admin role in Clerk public_metadata.
    
    Args:
        reject_req: Rejection request with invitation_id and optional reason
        admin_user_id: Admin user database ID
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 404 if invitation not found, 400 if already processed
    """
    engine = get_engine()
    invitation_id = UUID(reject_req.invitation_id)
    
    with get_connection(engine) as conn:
        # Get the invitation request
        result = conn.execute(
            select(invitation_requests_table.c.status, invitation_requests_table.c.email).where(
                invitation_requests_table.c.id == invitation_id
            )
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Invitation request not found")
        
        if result.status != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Invitation already {result.status}"
            )
        
        # Update request status
        conn.execute(
            update(invitation_requests_table)
            .where(invitation_requests_table.c.id == invitation_id)
            .values(
                status="rejected",
                reviewed_at=datetime.now(timezone.utc),
                reviewed_by=admin_user_id,
                rejection_reason=reject_req.reason,
            )
        )
        conn.commit()
        
        logger.info(
            "Invitation rejected",
            extra={
                "invitation_id": str(invitation_id),
                "email": result.email,
                "rejected_by": str(admin_user_id),
                "reason": reject_req.reason
            }
        )
        
        # Send polite rejection email
        try:
            # Need to get name from full record
            full_result = conn.execute(
                select(invitation_requests_table.c.name).where(
                    invitation_requests_table.c.id == invitation_id
                )
            ).fetchone()
            
            user_name = full_result[0] if (full_result and full_result[0]) else result.email.split("@")[0]
            email_html = render_rejection_email(user_name)
            email_sent = email_service.send_email(
                to=result.email,
                subject="Thank You for Your Interest in Dakora",
                html_content=email_html
            )
            
            if email_sent:
                logger.info(f"Rejection email sent to {result.email}")
            else:
                logger.warning(f"Failed to send rejection email to {result.email}")
        except Exception as e:
            logger.error(f"Error sending rejection email: {e}", exc_info=True)
        
        return {
            "message": "Invitation request rejected",
            "invitation_id": str(invitation_id)
        }
