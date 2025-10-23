"""Tests for Dakora client initialization"""

import os
import pytest
from dakora_client import Dakora


class TestDakoraClient:
    """Test Dakora client initialization and configuration"""

    async def test_init_with_explicit_params(self):
        """Test client initialization with explicit parameters"""
        client = Dakora(
            api_key="dk_test_key",
            base_url="https://test.dakora.io",
            project_id="test-project",
        )

        assert client.api_key == "dk_test_key"
        assert client.base_url == "https://test.dakora.io"
        assert client._project_id == "test-project"
        assert client.prompts is not None

        await client.close()

    async def test_init_with_env_vars(self, monkeypatch):
        """Test client initialization from environment variables"""
        monkeypatch.setenv("DAKORA_API_KEY", "dk_env_key")
        monkeypatch.setenv("DAKORA_BASE_URL", "https://env.dakora.io")

        client = Dakora()

        assert client.api_key == "dk_env_key"
        assert client.base_url == "https://env.dakora.io"

        await client.close()

    async def test_init_defaults(self):
        """Test client initialization with defaults"""
        client = Dakora()

        assert client.base_url == "https://api.dakora.io"
        assert client._project_id is None

        await client.close()

    async def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url"""
        client = Dakora(base_url="https://test.dakora.io/")

        assert client.base_url == "https://test.dakora.io"

        await client.close()

    async def test_get_project_id_lazy_loading(self, mock_project_context):
        """Test that project_id is fetched lazily from API"""
        client = Dakora(api_key="dk_test")

        # Should be None initially
        assert client._project_id is None

        # Should fetch from API
        project_id = await client._get_project_id()
        assert project_id == "test-project-123"

        # Should be cached now
        assert client._project_id == "test-project-123"

        await client.close()

    async def test_get_project_id_explicit(self):
        """Test that explicit project_id is used without API call"""
        client = Dakora(api_key="dk_test", project_id="explicit-project")

        # Should use explicit value
        project_id = await client._get_project_id()
        assert project_id == "explicit-project"

        await client.close()