"""Pytest fixtures for dakora-client tests"""

import pytest
import respx
from httpx import Response


@pytest.fixture
def mock_api():
    """Mock httpx requests using respx"""
    with respx.mock:
        yield respx


@pytest.fixture
def mock_project_context(mock_api):
    """Mock the /api/me/context endpoint"""
    mock_api.get("https://api.dakora.io/api/me/context").mock(
        return_value=Response(200, json={"project_id": "test-project-123"})
    )