"""User factory for creating test users."""

from uuid import UUID
from typing import Optional
from sqlalchemy import insert, select
from sqlalchemy.engine import Connection

from dakora_server.core.database import users_table
from .constants import (
    TEST_USER_ID,
    TEST_CLERK_USER_ID,
    TEST_USER_EMAIL,
    TEST_USER_NAME,
    make_test_user_id,
)


def create_test_user(
    conn: Connection,
    user_id: Optional[UUID] = None,
    clerk_user_id: Optional[str] = None,
    email: Optional[str] = None,
    name: Optional[str] = None,
    suffix: Optional[str] = None,
) -> UUID:
    """Create a test user in the database.

    Args:
        conn: Database connection
        user_id: User UUID (defaults to TEST_USER_ID or generated from suffix)
        clerk_user_id: Clerk user ID (defaults to TEST_CLERK_USER_ID or generated from suffix)
        email: User email (defaults to TEST_USER_EMAIL or generated from suffix)
        name: User name (defaults to TEST_USER_NAME)
        suffix: Suffix for generating unique IDs (overrides user_id/clerk_user_id/email)

    Returns:
        Created user's UUID

    Example:
        # Default test user
        user_id = create_test_user(conn)

        # User with custom values
        user_id = create_test_user(conn, email="custom@example.com")

        # Multiple users with suffix
        user1_id = create_test_user(conn, suffix="1")
        user2_id = create_test_user(conn, suffix="2")
    """
    if suffix:
        user_id = make_test_user_id(suffix)
        clerk_user_id = f"test_clerk_user_{suffix}"
        email = f"test{suffix}@example.com"
    else:
        user_id = user_id or TEST_USER_ID
        clerk_user_id = clerk_user_id or TEST_CLERK_USER_ID
        email = email or TEST_USER_EMAIL
        name = name or TEST_USER_NAME

    # Check if user already exists
    existing = conn.execute(
        select(users_table.c.id).where(users_table.c.id == user_id)
    ).fetchone()

    if existing:
        return user_id

    conn.execute(
        insert(users_table).values(
            id=user_id,
            clerk_user_id=clerk_user_id,
            email=email,
            name=name,
        )
    )

    return user_id
