"""Tests for PromptsAPI"""

import pytest
import pytest_asyncio
from httpx import Response
from dakora_client import Dakora

pytestmark = pytest.mark.asyncio


class TestPromptsAPI:
    """Test PromptsAPI methods"""

    @pytest_asyncio.fixture
    async def client(self, mock_project_context):
        """Create a test client"""
        client = Dakora(api_key="dk_test")
        yield client
        await client.close()

    async def test_list_prompts(self, client, mock_api):
        """Test listing all prompt templates"""
        mock_api.get("https://api.dakora.io/api/projects/test-project-123/prompts").mock(
            return_value=Response(200, json=["greeting", "email", "summary"])
        )

        templates = await client.prompts.list()

        assert templates == ["greeting", "email", "summary"]
        assert len(templates) == 3

    async def test_list_prompts_empty(self, client, mock_api):
        """Test listing prompts when none exist"""
        mock_api.get("https://api.dakora.io/api/projects/test-project-123/prompts").mock(
            return_value=Response(200, json=[])
        )

        templates = await client.prompts.list()

        assert templates == []

    async def test_render_prompt(self, client, mock_api):
        """Test rendering a prompt template with default embedded metadata"""
        mock_api.post("https://api.dakora.io/api/projects/test-project-123/prompts/greeting/render").mock(
            return_value=Response(200, json={"rendered": "Hello Alice!"})
        )

        result = await client.prompts.render("greeting", {"name": "Alice"})

        # Metadata is embedded by default
        assert "<!--dakora:prompt_id=greeting,version=latest-->" in result.text
        assert "Hello Alice!" in result.text
        assert result.prompt_id == "greeting"

    async def test_render_prompt_with_multiple_inputs(self, client, mock_api):
        """Test rendering with multiple input variables"""
        mock_api.post("https://api.dakora.io/api/projects/test-project-123/prompts/email/render").mock(
            return_value=Response(
                200,
                json={"rendered": "Dear Alice,\n\nYou are a Developer.\n\nBest regards"}
            )
        )

        result = await client.prompts.render(
            "email",
            {"name": "Alice", "role": "Developer"}
        )

        assert "Alice" in result.text
        assert "Developer" in result.text

    async def test_render_prompt_not_found(self, client, mock_api):
        """Test rendering a non-existent prompt"""
        mock_api.post("https://api.dakora.io/api/projects/test-project-123/prompts/nonexistent/render").mock(
            return_value=Response(404, json={"detail": "Template not found"})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await client.prompts.render("nonexistent", {})

    async def test_render_prompt_invalid_inputs(self, client, mock_api):
        """Test rendering with invalid inputs"""
        mock_api.post("https://api.dakora.io/api/projects/test-project-123/prompts/greeting/render").mock(
            return_value=Response(422, json={"detail": "Validation error"})
        )

        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await client.prompts.render("greeting", {})

    async def test_api_uses_project_id(self, client, mock_api):
        """Test that API calls use the correct project_id"""
        # Mock the list endpoint
        list_route = mock_api.get("https://api.dakora.io/api/projects/test-project-123/prompts")
        list_route.mock(return_value=Response(200, json=["test"]))

        await client.prompts.list()

        # Verify the correct URL was called
        assert list_route.called
        assert list_route.call_count == 1

    async def test_api_authentication_header(self, mock_project_context, mock_api):
        """Test that API key is sent in headers"""
        client = Dakora(api_key="dk_secret_key")

        # Mock the list endpoint and capture headers
        list_route = mock_api.get("https://api.dakora.io/api/projects/test-project-123/prompts")
        list_route.mock(return_value=Response(200, json=[]))

        await client.prompts.list()

        # Verify the API key header was sent
        assert list_route.called
        request = list_route.calls[0].request
        assert request.headers["X-API-Key"] == "dk_secret_key"

        await client.close()
