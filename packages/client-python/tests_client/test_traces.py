"""Tests for Dakora traces API client"""

import pytest
import respx
from httpx import Response
from dakora_client import Dakora

pytestmark = pytest.mark.asyncio


class TestTracesAPI:
    """Test traces API client methods"""

    async def test_list_traces_returns_list(self):
        """Test that list() returns a list of executions, not the full response object"""
        with respx.mock:
            client = Dakora(
                api_key="dk_test_key",
                base_url="https://test.dakora.io",
                project_id="test-project",
            )

            # Mock server response with pagination metadata
            mock_response = {
                "executions": [
                    {"trace_id": "trace-1", "session_id": "session-1"},
                    {"trace_id": "trace-2", "session_id": "session-1"},
                    {"trace_id": "trace-3", "session_id": "session-1"},
                ],
                "total": 3,
                "limit": 100,
                "offset": 0,
            }

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions?limit=100&offset=0"
            ).mock(return_value=Response(200, json=mock_response))

            # Call the list method
            traces = await client.traces.list(project_id="test-project")

            # Verify we get a list, not a dict
            assert isinstance(traces, list)
            assert len(traces) == 3  # Should be 3, not 4 (the number of keys in response)
            
            # Verify we can iterate over traces
            for trace in traces:
                assert "trace_id" in trace
                assert "session_id" in trace

            # Verify the first trace
            assert traces[0]["trace_id"] == "trace-1"

            await client.close()

    async def test_list_traces_with_metadata(self):
        """Test that list() with include_metadata=True returns full response"""
        with respx.mock:
            client = Dakora(
                api_key="dk_test_key",
                base_url="https://test.dakora.io",
                project_id="test-project",
            )

            # Mock server response
            mock_response = {
                "executions": [
                    {"trace_id": "trace-1", "session_id": "session-1"},
                    {"trace_id": "trace-2", "session_id": "session-1"},
                ],
                "total": 10,  # More traces available
                "limit": 2,
                "offset": 0,
            }

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions?limit=2&offset=0"
            ).mock(return_value=Response(200, json=mock_response))

            # Call the list method with include_metadata=True
            result = await client.traces.list(
                project_id="test-project",
                limit=2,
                include_metadata=True,
            )

            # Verify we get a dict with all metadata
            assert isinstance(result, dict)
            assert "executions" in result
            assert "total" in result
            assert "limit" in result
            assert "offset" in result

            # Verify pagination metadata
            assert len(result["executions"]) == 2
            assert result["total"] == 10
            assert result["limit"] == 2
            assert result["offset"] == 0

            await client.close()

    async def test_list_traces_with_filters(self):
        """Test that list() properly passes filter parameters"""
        with respx.mock:
            client = Dakora(
                api_key="dk_test_key",
                base_url="https://test.dakora.io",
                project_id="test-project",
            )

            mock_response = {
                "executions": [
                    {"trace_id": "trace-1", "session_id": "session-1", "agent_id": "agent-1"},
                ],
                "total": 1,
                "limit": 100,
                "offset": 0,
            }

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions"
            ).mock(return_value=Response(200, json=mock_response))

            # Call with filters
            traces = await client.traces.list(
                project_id="test-project",
                session_id="session-1",
                agent_id="agent-1",
            )

            # Verify we get the filtered list
            assert isinstance(traces, list)
            assert len(traces) == 1
            assert traces[0]["session_id"] == "session-1"
            assert traces[0]["agent_id"] == "agent-1"

            await client.close()

    async def test_list_traces_pagination(self):
        """Test that list() handles pagination correctly"""
        with respx.mock:
            client = Dakora(
                api_key="dk_test_key",
                base_url="https://test.dakora.io",
                project_id="test-project",
            )

            # Mock page 1
            page1_response = {
                "executions": [
                    {"trace_id": "trace-1"},
                    {"trace_id": "trace-2"},
                ],
                "total": 5,
                "limit": 2,
                "offset": 0,
            }

            # Mock page 2
            page2_response = {
                "executions": [
                    {"trace_id": "trace-3"},
                    {"trace_id": "trace-4"},
                ],
                "total": 5,
                "limit": 2,
                "offset": 2,
            }

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions?limit=2&offset=0"
            ).mock(return_value=Response(200, json=page1_response))

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions?limit=2&offset=2"
            ).mock(return_value=Response(200, json=page2_response))

            # Get page 1
            page1 = await client.traces.list(
                project_id="test-project",
                limit=2,
                offset=0,
                include_metadata=True,
            )

            assert isinstance(page1, dict)
            assert len(page1["executions"]) == 2
            assert page1["executions"][0]["trace_id"] == "trace-1"
            assert page1["offset"] == 0

            # Get page 2
            page2 = await client.traces.list(
                project_id="test-project",
                limit=2,
                offset=2,
                include_metadata=True,
            )

            assert isinstance(page2, dict)
            assert len(page2["executions"]) == 2
            assert page2["executions"][0]["trace_id"] == "trace-3"
            assert page2["offset"] == 2

            await client.close()

    async def test_list_traces_empty_result(self):
        """Test that list() handles empty results correctly"""
        with respx.mock:
            client = Dakora(
                api_key="dk_test_key",
                base_url="https://test.dakora.io",
                project_id="test-project",
            )

            mock_response = {
                "executions": [],
                "total": 0,
                "limit": 100,
                "offset": 0,
            }

            respx.get(
                "https://test.dakora.io/api/projects/test-project/executions?limit=100&offset=0"
            ).mock(return_value=Response(200, json=mock_response))

            traces = await client.traces.list(project_id="test-project")

            # Should return empty list, not error
            assert isinstance(traces, list)
            assert len(traces) == 0

            await client.close()

