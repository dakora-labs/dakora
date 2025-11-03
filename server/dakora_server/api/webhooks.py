"""Clerk webhook handlers for user lifecycle events."""

from typing import Any
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.engine import Engine
from svix.webhooks import Webhook, WebhookVerificationError

from ..config import settings, get_vault
from ..core.database import get_engine, get_connection, users_table
from ..core.provisioning import provision_workspace_and_project, provision_sample_data
from .me import invalidate_user_context_cache


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class ClerkWebhookEvent(BaseModel):
    """Clerk webhook event payload structure."""
    type: str
    data: dict[str, Any]


def verify_clerk_signature(payload: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Verify Clerk webhook signature using Svix library.

    Args:
        payload: Raw request body bytes
        headers: Request headers

    Returns:
        Parsed webhook payload as dict

    Raises:
        WebhookVerificationError: If signature verification fails
    """
    if not settings.clerk_webhook_secret:
        # If no webhook secret configured, skip verification (development only)
        import json
        return json.loads(payload)

    # Use official Svix library for verification
    wh = Webhook(settings.clerk_webhook_secret)
    return wh.verify(payload, headers)


def get_db_engine() -> Engine:
    """Dependency for database engine."""
    return get_engine()


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    engine: Engine = Depends(get_db_engine)
):
    """Handle Clerk webhook events.

    Processes user lifecycle events from Clerk:
    - user.created: Creates user record in database

    Args:
        request: FastAPI request object
        engine: Database engine dependency

    Returns:
        Success message

    Raises:
        HTTPException: 401 if signature verification fails
        HTTPException: 500 if database operation fails
    """
    # Read raw body for signature verification
    body = await request.body()

    # Verify webhook signature and get parsed payload
    try:
        event_data = verify_clerk_signature(body, dict(request.headers))
        event = ClerkWebhookEvent(**event_data)
    except WebhookVerificationError as e:
        raise HTTPException(status_code=401, detail=f"Invalid webhook signature: {str(e)}")

    # Handle user.created event
    if event.type == "user.created":
        user_data = event.data

        # Extract user info from Clerk payload
        clerk_user_id = user_data.get("id")
        email_addresses = user_data.get("email_addresses", [])
        first_name = user_data.get("first_name")
        last_name = user_data.get("last_name")

        # Get primary email
        primary_email = None
        for email_obj in email_addresses:
            if email_obj.get("id") == user_data.get("primary_email_address_id"):
                primary_email = email_obj.get("email_address")
                break

        # Fallback to first email if no primary
        if not primary_email and email_addresses:
            primary_email = email_addresses[0].get("email_address")

        if not clerk_user_id or not primary_email:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: id or email"
            )

        # Build full name
        name_parts = []
        if first_name:
            name_parts.append(first_name)
        if last_name:
            name_parts.append(last_name)
        full_name = " ".join(name_parts) if name_parts else None

        # Insert user into database
        try:
            with get_connection(engine) as conn:
                # Check if user already exists
                result = conn.execute(
                    users_table.select().where(
                        users_table.c.clerk_user_id == clerk_user_id
                    )
                ).fetchone()

                if result is None:
                    # Insert new user
                    user_result = conn.execute(
                        users_table.insert().values(
                            clerk_user_id=clerk_user_id,
                            email=primary_email,
                            name=full_name,
                        ).returning(users_table.c.id)
                    )
                    user_id = user_result.fetchone()[0]

                    # Auto-provision workspace and default project
                    workspace_id, project_id = provision_workspace_and_project(
                        conn, user_id, full_name, primary_email
                    )

                    # Commit critical user data first
                    # This ensures user creation succeeds even if sample provisioning fails
                    conn.commit()

                    # Provision sample prompts and parts AFTER commit (non-blocking)
                    # This happens outside the main transaction so it won't rollback user creation
                    try:
                        base_vault = get_vault()
                        provision_sample_data(
                            conn, engine, project_id, base_vault.registry
                        )
                    except Exception as e:
                        # Log error but don't fail the webhook
                        import logging
                        logging.getLogger(__name__).error(
                            f"Failed to provision sample data: {e}"
                        )

                    # Invalidate cache for new user (though unlikely to exist)
                    invalidate_user_context_cache(clerk_user_id)

                    return {
                        "status": "success",
                        "message": "User created with workspace and project",
                        "user_id": clerk_user_id,
                        "workspace_id": str(workspace_id),
                        "project_id": str(project_id)
                    }
                else:
                    # User already exists (webhook replay or duplicate)
                    return {
                        "status": "success",
                        "message": "User already exists",
                        "user_id": clerk_user_id
                    }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )

    # Handle user.updated event
    if event.type == "user.updated":
        user_data = event.data
        clerk_user_id = user_data.get("id")
        
        if clerk_user_id:
            # Invalidate cache so next request gets fresh data
            invalidate_user_context_cache(clerk_user_id)
            return {
                "status": "success",
                "message": "User updated, cache invalidated",
                "user_id": clerk_user_id
            }

    # Handle user.deleted event
    if event.type == "user.deleted":
        user_data = event.data
        clerk_user_id = user_data.get("id")
        
        if clerk_user_id:
            # Invalidate cache for deleted user
            invalidate_user_context_cache(clerk_user_id)
            return {
                "status": "success",
                "message": "User deleted, cache invalidated",
                "user_id": clerk_user_id
            }

    # Ignore other event types
    return {"status": "success", "message": f"Event {event.type} received but not processed"}