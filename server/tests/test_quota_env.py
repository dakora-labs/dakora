"""Tests for quota tier environment variable configuration."""

import os
import pytest

from dakora_server.core.llm.quota import _parse_quota_tiers


def test_parse_default_tiers():
    """Test parsing default tiers when no env var set."""
    # Clear env var if set
    original = os.environ.pop("TOKEN_QUOTA_TIERS", None)
    try:
        tiers = _parse_quota_tiers()
        assert tiers == {
            "free": 100_000,
            "starter": 1_000_000,
            "pro": 10_000_000,
        }
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original


def test_parse_custom_tiers():
    """Test parsing custom tiers from env var."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = "free=50000,starter=500000,pro=5000000"
        tiers = _parse_quota_tiers()
        assert tiers == {
            "free": 50_000,
            "starter": 500_000,
            "pro": 5_000_000,
        }
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)


def test_parse_custom_tier_names():
    """Test parsing with custom tier names."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = "basic=10000,premium=100000,enterprise=1000000"
        tiers = _parse_quota_tiers()
        assert tiers == {
            "basic": 10_000,
            "premium": 100_000,
            "enterprise": 1_000_000,
        }
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)


def test_parse_invalid_format_missing_equals():
    """Test parsing fails with invalid format (missing =)."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = "free100000,starter1000000"
        with pytest.raises(ValueError, match="Invalid tier format.*Expected 'tier=limit'"):
            _parse_quota_tiers()
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)


def test_parse_invalid_limit_not_number():
    """Test parsing fails with non-numeric limit."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = "free=abc,starter=1000000"
        with pytest.raises(ValueError, match="Invalid tier limit for 'free'"):
            _parse_quota_tiers()
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)


def test_parse_negative_limit():
    """Test parsing fails with negative limit."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = "free=-100,starter=1000000"
        with pytest.raises(ValueError, match="Tier limit must be non-negative"):
            _parse_quota_tiers()
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)


def test_parse_with_whitespace():
    """Test parsing handles whitespace correctly."""
    original = os.environ.get("TOKEN_QUOTA_TIERS")
    try:
        os.environ["TOKEN_QUOTA_TIERS"] = " free = 100000 , starter = 1000000 "
        tiers = _parse_quota_tiers()
        assert tiers == {
            "free": 100_000,
            "starter": 1_000_000,
        }
    finally:
        if original:
            os.environ["TOKEN_QUOTA_TIERS"] = original
        else:
            os.environ.pop("TOKEN_QUOTA_TIERS", None)