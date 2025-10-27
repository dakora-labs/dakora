"""Tests for related traces endpoint"""

import pytest
from uuid import uuid4


@pytest.mark.integration
class TestRelatedTraces:
    """Tests for GET /api/projects/{project_id}/executions/{trace_id}/related"""

    def test_get_related_traces_with_parent(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving related traces when trace has a parent"""
        project_id, _, _ = test_project
        
        # Create parent trace
        parent_trace_id = str(uuid4())
        session_id = str(uuid4())
        
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "parent-agent",
                "conversation_history": [{"role": "user", "content": "Parent request"}],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens_in": 100,
                "tokens_out": 50,
                "latency_ms": 1000,
            },
        )
        
        # Create child trace
        child_trace_id = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": child_trace_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "child-agent",
                "conversation_history": [{"role": "assistant", "content": "Child response"}],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens_in": 50,
                "tokens_out": 75,
                "latency_ms": 800,
            },
        )
        
        # Create sibling trace
        sibling_trace_id = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": sibling_trace_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "sibling-agent",
                "conversation_history": [{"role": "assistant", "content": "Sibling response"}],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens_in": 60,
                "tokens_out": 80,
                "latency_ms": 900,
            },
        )
        
        # Get related traces for child
        response = test_client.get(f"/api/projects/{project_id}/executions/{child_trace_id}/related")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert data["trace_id"] == child_trace_id
        assert data["parent"] is not None
        assert data["parent"]["trace_id"] == parent_trace_id
        assert data["parent"]["agent_id"] == "parent-agent"
        assert data["parent"]["tokens_in"] == 100
        assert data["parent"]["tokens_out"] == 50
        
        # Verify siblings
        assert len(data["siblings"]) == 1
        assert data["siblings"][0]["trace_id"] == sibling_trace_id
        assert data["siblings"][0]["agent_id"] == "sibling-agent"
        
        # Verify children (should be empty for child trace)
        assert len(data["children"]) == 0
        
        # Verify session agents
        assert len(data["session_agents"]) == 3
        agent_ids = {agent["agent_id"] for agent in data["session_agents"]}
        assert agent_ids == {"parent-agent", "child-agent", "sibling-agent"}

    def test_get_related_traces_for_parent(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving related traces for parent trace"""
        project_id, _, _ = test_project
        
        parent_trace_id = str(uuid4())
        session_id = str(uuid4())
        
        # Create parent
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "orchestrator",
                "conversation_history": [{"role": "user", "content": "Main request"}],
                "provider": "openai",
                "model": "gpt-4o",
                "tokens_in": 200,
                "tokens_out": 100,
                "latency_ms": 2000,
            },
        )
        
        # Create two children
        child1_id = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": child1_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "researcher",
                "conversation_history": [{"role": "assistant", "content": "Research result"}],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens_in": 150,
                "tokens_out": 200,
                "latency_ms": 1500,
            },
        )
        
        child2_id = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": child2_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "writer",
                "conversation_history": [{"role": "assistant", "content": "Written content"}],
                "provider": "openai",
                "model": "gpt-4o-mini",
                "tokens_in": 180,
                "tokens_out": 250,
                "latency_ms": 1800,
            },
        )
        
        # Get related traces for parent
        response = test_client.get(f"/api/projects/{project_id}/executions/{parent_trace_id}/related")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["trace_id"] == parent_trace_id
        assert data["parent"] is None  # Parent has no parent
        assert len(data["siblings"]) == 0  # Parent has no siblings
        assert len(data["children"]) == 2  # Parent has two children
        
        child_ids = {child["trace_id"] for child in data["children"]}
        assert child_ids == {child1_id, child2_id}
        
        # Verify session has all agents
        assert len(data["session_agents"]) == 3
        agent_ids = {agent["agent_id"] for agent in data["session_agents"]}
        assert agent_ids == {"orchestrator", "researcher", "writer"}

    def test_get_related_traces_standalone(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving related traces for standalone trace (no parent, no children)"""
        project_id, _, _ = test_project
        
        trace_id = str(uuid4())
        session_id = str(uuid4())
        
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
                "agent_id": "standalone-agent",
                "conversation_history": [{"role": "user", "content": "Solo request"}],
                "provider": "openai",
                "model": "gpt-4o",
                "tokens_in": 50,
                "tokens_out": 30,
                "latency_ms": 500,
            },
        )
        
        response = test_client.get(f"/api/projects/{project_id}/executions/{trace_id}/related")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["trace_id"] == trace_id
        assert data["parent"] is None
        assert len(data["siblings"]) == 0
        assert len(data["children"]) == 0
        assert len(data["session_agents"]) == 1
        assert data["session_agents"][0]["agent_id"] == "standalone-agent"
        assert data["session_agents"][0]["trace_count"] == 1

    def test_get_related_traces_not_found(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving related traces for non-existent trace"""
        project_id, _, _ = test_project
        non_existent_trace = str(uuid4())
        
        response = test_client.get(f"/api/projects/{project_id}/executions/{non_existent_trace}/related")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
