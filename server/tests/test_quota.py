"""Tests for quota management."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from dakora_server.core.llm import QUOTA_TIERS, QuotaService
from dakora_server.core.database import get_engine


@pytest.fixture
def quota_service():
    """Create quota service instance."""
    return QuotaService()


@pytest_asyncio.fixture
async def test_user_id():
    """Create test user."""
    user_id = str(uuid.uuid4())
    engine = get_engine()

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO users (id, clerk_user_id, email, name)
                VALUES (:id, :clerk_user_id, :email, :name)
            """),
            {
                "id": user_id,
                "clerk_user_id": f"user_{user_id[:8]}",
                "email": f"test-{user_id[:8]}@example.com",
                "name": "Test User",
            },
        )
        conn.commit()

    yield user_id

    # Cleanup
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        conn.commit()


@pytest_asyncio.fixture
async def test_workspace_id(quota_service, test_user_id):
    """Create test workspace with quota."""
    workspace_id = str(uuid.uuid4())

    # Create workspace in database first
    engine = get_engine()
    with engine.connect() as conn:
        # Insert test workspace
        conn.execute(
            text("""
                INSERT INTO workspaces (id, slug, name, type, owner_id)
                VALUES (:id, :slug, :name, 'personal', :owner_id)
            """),
            {
                "id": workspace_id,
                "slug": f"test-{workspace_id[:8]}",
                "name": "Test Workspace",
                "owner_id": test_user_id,
            },
        )
        conn.commit()

    # Create quota
    await quota_service.create_quota(workspace_id, tier="free")

    yield workspace_id

    # Cleanup
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM workspace_quotas WHERE workspace_id = :id"),
            {"id": workspace_id},
        )
        conn.execute(
            text("DELETE FROM workspaces WHERE id = :id"), {"id": workspace_id}
        )
        conn.commit()


@pytest.mark.asyncio
async def test_create_quota(quota_service, test_workspace_id):
    """Test quota creation."""
    usage = await quota_service.get_usage(test_workspace_id)

    assert usage.workspace_id == test_workspace_id
    assert usage.tier == "free"
    assert usage.tokens_used == 0
    assert usage.tokens_limit == QUOTA_TIERS["free"]
    assert usage.tokens_remaining == QUOTA_TIERS["free"]
    assert usage.usage_percentage == 0.0


@pytest.mark.asyncio
async def test_check_quota_available(quota_service, test_workspace_id):
    """Test quota check with available tokens."""
    has_quota = await quota_service.check_quota(test_workspace_id)
    assert has_quota is True


@pytest.mark.asyncio
async def test_consume_quota(quota_service, test_workspace_id):
    """Test consuming quota."""
    tokens_to_consume = 1000

    # Consume tokens
    await quota_service.consume_quota(test_workspace_id, tokens_to_consume)

    # Check updated usage
    usage = await quota_service.get_usage(test_workspace_id)
    assert usage.tokens_used == tokens_to_consume
    assert usage.tokens_remaining == QUOTA_TIERS["free"] - tokens_to_consume


@pytest.mark.asyncio
async def test_consume_quota_multiple_times(quota_service, test_workspace_id):
    """Test consuming quota multiple times."""
    await quota_service.consume_quota(test_workspace_id, 500)
    await quota_service.consume_quota(test_workspace_id, 300)
    await quota_service.consume_quota(test_workspace_id, 200)

    usage = await quota_service.get_usage(test_workspace_id)
    assert usage.tokens_used == 1000


@pytest.mark.asyncio
async def test_check_quota_exceeded(quota_service, test_workspace_id):
    """Test quota check when limit is exceeded."""
    # Consume all available quota
    await quota_service.consume_quota(
        test_workspace_id, QUOTA_TIERS["free"]
    )

    has_quota = await quota_service.check_quota(test_workspace_id)
    assert has_quota is False


@pytest.mark.asyncio
async def test_quota_usage_percentage(quota_service, test_workspace_id):
    """Test usage percentage calculation."""
    # Use 50% of quota
    half_quota = QUOTA_TIERS["free"] // 2
    await quota_service.consume_quota(test_workspace_id, half_quota)

    usage = await quota_service.get_usage(test_workspace_id)
    assert 49.0 <= usage.usage_percentage <= 51.0  # Allow small rounding errors


@pytest.mark.asyncio
async def test_create_quota_invalid_tier(quota_service):
    """Test creating quota with invalid tier."""
    workspace_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="Invalid tier"):
        await quota_service.create_quota(workspace_id, tier="invalid")


@pytest.mark.asyncio
async def test_consume_quota_auto_creates_quota(quota_service, test_user_id):
    """Test consuming quota auto-creates quota for existing workspace without one."""
    workspace_id = str(uuid.uuid4())
    engine = get_engine()

    # Create workspace without quota (backwards compatibility scenario)
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO workspaces (id, slug, name, type, owner_id)
                VALUES (:id, :slug, :name, 'personal', :owner_id)
            """),
            {
                "id": workspace_id,
                "slug": f"test-autocreate-{workspace_id[:8]}",
                "name": "Test Auto-Create Workspace",
                "owner_id": test_user_id,
            },
        )
        conn.commit()

    # Consume quota should auto-create and not raise
    await quota_service.consume_quota(workspace_id, 100)

    # Verify quota was created with free tier
    usage = await quota_service.get_usage(workspace_id)
    assert usage.tier == "free"
    assert usage.tokens_used == 100
    assert usage.tokens_limit == QUOTA_TIERS["free"]

    # Cleanup
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM workspace_quotas WHERE workspace_id = :id"),
            {"id": workspace_id},
        )
        conn.execute(
            text("DELETE FROM workspaces WHERE id = :id"),
            {"id": workspace_id},
        )
        conn.commit()


@pytest.mark.asyncio
async def test_get_usage_auto_creates_quota(quota_service, test_user_id):
    """Test getting usage auto-creates quota for existing workspace without one."""
    workspace_id = str(uuid.uuid4())
    engine = get_engine()

    # Create workspace without quota (backwards compatibility scenario)
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO workspaces (id, slug, name, type, owner_id)
                VALUES (:id, :slug, :name, 'personal', :owner_id)
            """),
            {
                "id": workspace_id,
                "slug": f"test-getusage-{workspace_id[:8]}",
                "name": "Test Get Usage Workspace",
                "owner_id": test_user_id,
            },
        )
        conn.commit()

    # Get usage should auto-create and not raise
    usage = await quota_service.get_usage(workspace_id)

    # Verify quota was created with free tier
    assert usage.tier == "free"
    assert usage.tokens_used == 0
    assert usage.tokens_limit == QUOTA_TIERS["free"]

    # Cleanup
    with engine.connect() as conn:
        conn.execute(
            text("DELETE FROM workspace_quotas WHERE workspace_id = :id"),
            {"id": workspace_id},
        )
        conn.execute(
            text("DELETE FROM workspaces WHERE id = :id"),
            {"id": workspace_id},
        )
        conn.commit()


@pytest.mark.asyncio
async def test_auto_reset_period(quota_service, test_workspace_id):
    """Test automatic quota reset when period ends."""
    engine = get_engine()

    # Consume some tokens
    await quota_service.consume_quota(test_workspace_id, 5000)

    # Verify tokens consumed
    usage = await quota_service.get_usage(test_workspace_id)
    assert usage.tokens_used == 5000

    # Manually set period end to past date
    with engine.connect() as conn:
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        conn.execute(
            text("""
                UPDATE workspace_quotas
                SET current_period_end = :past_date
                WHERE workspace_id = :workspace_id
            """),
            {"past_date": past_date, "workspace_id": test_workspace_id},
        )
        conn.commit()

    # Get usage again - should trigger auto-reset
    usage = await quota_service.get_usage(test_workspace_id)
    assert usage.tokens_used == 0
    assert usage.tokens_limit == QUOTA_TIERS["free"]


@pytest.mark.asyncio
async def test_quota_tiers():
    """Test quota tier definitions."""
    assert QUOTA_TIERS["free"] == 100_000
    assert QUOTA_TIERS["starter"] == 1_000_000
    assert QUOTA_TIERS["pro"] == 10_000_000


@pytest.mark.asyncio
async def test_create_quota_different_tiers(quota_service, test_user_id):
    """Test creating quotas with different tiers."""
    engine = get_engine()

    for tier, expected_limit in QUOTA_TIERS.items():
        workspace_id = str(uuid.uuid4())

        # Create workspace
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO workspaces (id, slug, name, type, owner_id)
                    VALUES (:id, :slug, :name, 'personal', :owner_id)
                """),
                {
                    "id": workspace_id,
                    "slug": f"test-{tier}-{workspace_id[:8]}",
                    "name": f"Test {tier} Workspace",
                    "owner_id": test_user_id,
                },
            )
            conn.commit()

        # Create quota with tier
        usage = await quota_service.create_quota(workspace_id, tier=tier)

        assert usage.tier == tier
        assert usage.tokens_limit == expected_limit
        assert usage.tokens_used == 0

        # Cleanup
        with engine.connect() as conn:
            conn.execute(
                text("DELETE FROM workspace_quotas WHERE workspace_id = :id"),
                {"id": workspace_id},
            )
            conn.execute(
                text("DELETE FROM workspaces WHERE id = :id"),
                {"id": workspace_id},
            )
            conn.commit()