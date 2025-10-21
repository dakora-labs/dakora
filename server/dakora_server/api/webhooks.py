"""Clerk webhook handlers for user lifecycle events."""

import hmac
import hashlib
from typing import Any
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.engine import Engine

from ..config import settings
from ..core.database import create_db_engine, get_connection, users_table


router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class ClerkWebhookEvent(BaseModel):
    """Clerk webhook event payload structure."""
    type: str
    data: dict[str, Any]


def verify_clerk_signature(payload: bytes, headers: dict[str, str]) -> bool:
    """Verify Clerk webhook signature.

    Args:
        payload: Raw request body bytes
        headers: Request headers

    Returns:
        True if signature is valid, False otherwise
    """
    if not settings.clerk_webhook_secret:
        # If no webhook secret configured, skip verification (development only)
        return True

    signature = headers.get("svix-signature")
    if not signature:
        return False

    # Clerk uses Svix for webhooks, signature format: "v1,signature"
    # Extract the actual signature value
    sig_parts = {}
    for part in signature.split(" "):
        if "," in part:
            key, value = part.split(",", 1)
            sig_parts[key] = value

    expected_signature = sig_parts.get("v1")
    if not expected_signature:
        return False

    # Compute HMAC-SHA256
    computed = hmac.new(
        settings.clerk_webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, expected_signature)


def get_db_engine() -> Engine:
    """Dependency for database engine."""
    return create_db_engine()


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

    # Verify webhook signature
    if not verify_clerk_signature(body, dict(request.headers)):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse event
    event_data = await request.json()
    event = ClerkWebhookEvent(**event_data)

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
                    conn.execute(
                        users_table.insert().values(
                            clerk_user_id=clerk_user_id,
                            email=primary_email,
                            name=full_name,
                        )
                    )
                    conn.commit()

                    return {
                        "status": "success",
                        "message": "User created",
                        "user_id": clerk_user_id
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

    # Ignore other event types
    return {"status": "success", "message": f"Event {event.type} received but not processed"}