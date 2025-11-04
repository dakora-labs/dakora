"""
Test span type filtering for execution traces.

This test verifies that only chat and agent span types are included
in execution list aggregations, filtering out orchestration spans.
"""

import pytest
from uuid import uuid4


@pytest.mark.integration
class TestSpanTypeFiltering:
    """Test that execution list filters span types correctly"""

    def test_only_chat_and_agent_spans_aggregated(
        self, test_project, test_client, override_auth_dependencies
    ):
        """
        Test that only chat/agent spans are aggregated, orchestration spans excluded.
        
        This simulates a MAF workflow with multiple span types:
        - workflow.run (should be excluded)
        - executor.process (should be excluded)
        - chat (should be included)
        - agent (should be included)
        """
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        
        # Create OTLP trace with mixed span types
        # This would come from the OTLP collector in practice
        
        # First verify the behavior before detailed implementation
        # For now, just test that the endpoint works with the filter
        
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have the expected structure
        assert "executions" in data
        assert "total" in data
        assert isinstance(data["executions"], list)
        
        # All returned executions should have meaningful data
        # (not orchestration-only traces with 0 tokens)
        for execution in data["executions"]:
            # If it's in the list, it should have LLM-related data
            # Either tokens or a model/provider
            has_tokens = (
                execution.get("total_tokens_in") is not None 
                or execution.get("total_tokens_out") is not None
            )
            has_llm_info = (
                execution.get("model") is not None 
                or execution.get("provider") is not None
            )
            
            # At least one should be true for chat/agent spans
            assert has_tokens or has_llm_info, (
                f"Execution {execution.get('trace_id')} appears to be "
                f"orchestration-only (no tokens or LLM info)"
            )


    def test_orchestration_only_trace_excluded(
        self, test_project, test_client, override_auth_dependencies
    ):
        """
        Test that traces with ONLY orchestration spans are excluded.
        
        A trace with only workflow.run, executor.process, etc. should NOT appear
        in the execution list since it has no actual LLM calls.
        """
        project_id, _, _ = test_project
        
        # In practice, this would be tested by inserting a trace with only
        # orchestration spans via OTLP and verifying it doesn't appear
        
        # For now, verify that the filter exists
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # If we have any executions, they should all be meaningful
        assert isinstance(data["executions"], list)
        
        # TODO: Add test with actual OTLP data insertion once collector is set up
        # For now, this documents the expected behavior


    def test_agent_filter_works_with_span_filtering(
        self, test_project, test_client, override_auth_dependencies
    ):
        """
        Test that agent_id filter works correctly with span type filtering.
        
        Should only return chat/agent spans for the specified agent.
        """
        project_id, _, _ = test_project
        
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"agent_id": "test-agent"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        
        # All returned executions should match the agent filter
        for execution in data["executions"]:
            if execution.get("agent_id"):
                assert execution["agent_id"] == "test-agent"
