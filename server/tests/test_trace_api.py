"""Integration tests for trace telemetry API endpoints.

This test suite covers the trace-based execution logging system
for observability from MAF middleware.
"""

import pytest
from uuid import uuid4


@pytest.mark.integration
class TestCreateExecution:
    """Tests for POST /api/projects/{project_id}/executions"""

    def test_create_execution_minimal(self, test_project, test_client, override_auth_dependencies):
        """Test creating execution with minimal required fields"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        session_id = str(uuid4())

        response = test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id
        assert data["status"] == "logged"

    def test_create_execution_full_observability(self, test_project, test_client, override_auth_dependencies):
        """Test creating execution with full observability data"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        session_id = str(uuid4())
        parent_trace_id = str(uuid4())

        response = test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "test-agent",
                "conversation_history": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                ],
                "metadata": {"environment": "test", "version": "1.0"},
                "provider": "openai",
                "model": "gpt-4",
                "tokens_in": 10,
                "tokens_out": 15,
                "cost_usd": 0.001,
                "latency_ms": 250,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id
        assert data["status"] == "logged"

    def test_create_execution_with_template_usage(self, test_project, test_client, override_auth_dependencies):
        """Test creating execution with linked template usage"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        session_id = str(uuid4())

        response = test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
                "template_usages": [
                    {
                        "prompt_id": "greeting-template",
                        "version": "1.0.0",
                        "inputs": {"name": "Alice"},
                    }
                ],
                "provider": "openai",
                "model": "gpt-4",
                "tokens_in": 10,
                "tokens_out": 15,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id

    def test_create_execution_with_multiple_templates(self, test_project, test_client, override_auth_dependencies):
        """Test creating execution using multiple templates"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        session_id = str(uuid4())

        response = test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
                "template_usages": [
                    {
                        "prompt_id": "system-prompt",
                        "version": "1.0.0",
                        "inputs": {},
                    },
                    {
                        "prompt_id": "user-query",
                        "version": "2.1.0",
                        "inputs": {"query": "What is AI?"},
                    },
                ],
                "provider": "anthropic",
                "model": "claude-3-opus",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["trace_id"] == trace_id

    def test_create_execution_unauthorized(self, test_project, test_client):
        """Test creating execution without authentication"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())

        response = test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": str(uuid4()),
            },
        )

        assert response.status_code == 401

    def test_create_execution_invalid_project(self, test_client, db_connection):
        """Test creating execution for non-existent project
        
        This test bypasses auth overrides to test the real validate_project_access,
        which should return 404 when project doesn't exist.
        """
        from dakora_server.auth import get_auth_context, AuthContext
        from dakora_server.main import app
        
        invalid_project_id = str(uuid4())
        trace_id = str(uuid4())

        # Set up minimal auth that won't validate project existence
        async def mock_auth():
            return AuthContext(user_id="test-user", project_id=None, auth_method="none")
        
        app.dependency_overrides[get_auth_context] = mock_auth

        try:
            response = test_client.post(
                f"/api/projects/{invalid_project_id}/executions",
                json={
                    "trace_id": trace_id,
                    "session_id": str(uuid4()),
                },
            )

            # Should get 404 from validate_project_access
            assert response.status_code == 404
        finally:
            # Clean up override
            app.dependency_overrides.pop(get_auth_context, None)


@pytest.mark.integration
class TestListExecutions:
    """Tests for GET /api/projects/{project_id}/executions"""

    def test_list_executions_empty(self, test_project, test_client, override_auth_dependencies):
        """Test listing executions when none exist"""
        project_id, _, _ = test_project

        response = test_client.get(f"/api/projects/{project_id}/executions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May have some executions from other tests, so just check it's a list

    def test_list_executions_with_data(self, test_project, test_client, override_auth_dependencies):
        """Test listing executions after creating some"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        # Create multiple executions
        trace_ids = []
        for i in range(3):
            trace_id = str(uuid4())
            trace_ids.append(trace_id)

            test_client.post(
                f"/api/projects/{project_id}/executions",
                json={
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "agent_id": f"agent-{i}",
                    "provider": "openai",
                    "model": "gpt-4",
                    "tokens_in": 10 + i,
                    "tokens_out": 20 + i,
                    "cost_usd": 0.001 * (i + 1),
                    "latency_ms": 100 + i * 50,
                },
            )

        # List executions
        response = test_client.get(f"/api/projects/{project_id}/executions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Find our executions in the list
        our_executions = [e for e in data if e["trace_id"] in trace_ids]
        assert len(our_executions) == 3

        # Verify structure of returned data
        for execution in our_executions:
            assert "trace_id" in execution
            assert "session_id" in execution
            assert "provider" in execution
            assert "model" in execution
            assert "tokens_in" in execution
            assert "tokens_out" in execution
            assert "cost_usd" in execution
            assert "latency_ms" in execution
            assert "created_at" in execution

    def test_list_executions_filter_by_session(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by session_id"""
        project_id, _, _ = test_project
        session_id_1 = str(uuid4())
        session_id_2 = str(uuid4())

        # Create executions in different sessions
        trace_1 = str(uuid4())
        trace_2 = str(uuid4())

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": trace_1, "session_id": session_id_1},
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": trace_2, "session_id": session_id_2},
        )

        # Filter by session_id_1
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id_1},
        )

        assert response.status_code == 200
        data = response.json()

        # Should only contain executions from session_id_1
        matching = [e for e in data if e["trace_id"] == trace_1]
        assert len(matching) == 1
        assert matching[0]["session_id"] == session_id_1

    def test_list_executions_filter_by_agent(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by agent_id"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        # Create executions with different agents
        trace_1 = str(uuid4())
        trace_2 = str(uuid4())

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": trace_1, "session_id": session_id, "agent_id": "agent-A"},
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": trace_2, "session_id": session_id, "agent_id": "agent-B"},
        )

        # Filter by agent-A
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"agent_id": "agent-A"},
        )

        assert response.status_code == 200
        data = response.json()

        matching = [e for e in data if e["trace_id"] == trace_1]
        assert len(matching) == 1
        assert matching[0]["agent_id"] == "agent-A"

    def test_list_executions_filter_by_prompt(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by prompt_id"""
        project_id, _, _ = test_project
        session_id = str(uuid4())
        prompt_id = "test-prompt"

        # Create execution with template usage
        trace_1 = str(uuid4())
        trace_2 = str(uuid4())

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_1,
                "session_id": session_id,
                "template_usages": [
                    {"prompt_id": prompt_id, "version": "1.0.0", "inputs": {}}
                ],
            },
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_2,
                "session_id": session_id,
                "template_usages": [
                    {"prompt_id": "other-prompt", "version": "1.0.0", "inputs": {}}
                ],
            },
        )

        # Filter by prompt_id
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"prompt_id": prompt_id},
        )

        assert response.status_code == 200
        data = response.json()

        # Should find trace_1
        matching = [e for e in data if e["trace_id"] == trace_1]
        assert len(matching) == 1

    def test_list_executions_pagination(self, test_project, test_client, override_auth_dependencies):
        """Test pagination of execution list"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        # Create multiple executions
        for i in range(5):
            test_client.post(
                f"/api/projects/{project_id}/executions",
                json={"trace_id": str(uuid4()), "session_id": session_id},
            )

        # Test limit
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"limit": 2},
        )

        assert response.status_code == 200
        # Response should respect limit parameter

        # Test offset
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"limit": 10, "offset": 0},
        )

        assert response.status_code == 200


@pytest.mark.integration
class TestGetExecution:
    """Tests for GET /api/projects/{project_id}/executions/{trace_id}"""

    def test_get_execution_details(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving detailed execution information"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        parent_trace_id = str(uuid4())
        session_id = str(uuid4())

        conversation_history = [
            {"role": "user", "content": "What is the weather?"},
            {"role": "assistant", "content": "The weather is sunny."},
        ]

        metadata = {"environment": "production", "version": "2.0"}

        # Create execution
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "session_id": session_id,
                "agent_id": "weather-bot",
                "conversation_history": conversation_history,
                "metadata": metadata,
                "provider": "openai",
                "model": "gpt-4",
                "tokens_in": 25,
                "tokens_out": 30,
                "cost_usd": 0.002,
                "latency_ms": 350,
            },
        )

        # Retrieve execution
        response = test_client.get(f"/api/projects/{project_id}/executions/{trace_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all fields
        assert data["trace_id"] == trace_id
        assert data["parent_trace_id"] == parent_trace_id
        assert data["session_id"] == session_id
        assert data["agent_id"] == "weather-bot"
        assert data["conversation_history"] == conversation_history
        assert data["metadata"] == metadata
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4"
        assert data["tokens_in"] == 25
        assert data["tokens_out"] == 30
        assert data["cost_usd"] == 0.002
        assert data["latency_ms"] == 350
        assert "created_at" in data
        assert isinstance(data["templates_used"], list)

    def test_get_execution_with_templates(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving execution with linked templates"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())
        session_id = str(uuid4())

        template_usages = [
            {
                "prompt_id": "greeting",
                "version": "1.0.0",
                "inputs": {"name": "Bob"},
            },
            {
                "prompt_id": "farewell",
                "version": "1.2.0",
                "inputs": {"name": "Bob"},
            },
        ]

        # Create execution
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_id,
                "session_id": session_id,
                "template_usages": template_usages,
            },
        )

        # Retrieve execution
        response = test_client.get(f"/api/projects/{project_id}/executions/{trace_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify template linkage
        assert len(data["templates_used"]) == 2

        # Templates should be in order
        assert data["templates_used"][0]["prompt_id"] == "greeting"
        assert data["templates_used"][0]["version"] == "1.0.0"
        assert data["templates_used"][0]["inputs"] == {"name": "Bob"}
        assert data["templates_used"][0]["position"] == 0

        assert data["templates_used"][1]["prompt_id"] == "farewell"
        assert data["templates_used"][1]["version"] == "1.2.0"
        assert data["templates_used"][1]["position"] == 1

    def test_get_execution_not_found(self, test_project, test_client, override_auth_dependencies):
        """Test retrieving non-existent execution"""
        project_id, _, _ = test_project
        nonexistent_trace_id = str(uuid4())

        response = test_client.get(
            f"/api/projects/{project_id}/executions/{nonexistent_trace_id}"
        )

        assert response.status_code == 404

    def test_get_execution_unauthorized(self, test_project, test_client):
        """Test retrieving execution without authentication"""
        project_id, _, _ = test_project
        trace_id = str(uuid4())

        response = test_client.get(f"/api/projects/{project_id}/executions/{trace_id}")

        assert response.status_code == 401


@pytest.mark.integration
class TestTemplateAnalytics:
    """Tests for GET /api/projects/{project_id}/prompts/{prompt_id}/analytics"""

    def test_template_analytics_no_usage(self, test_project, test_client, override_auth_dependencies):
        """Test analytics for template that hasn't been used"""
        project_id, _, _ = test_project
        prompt_id = "unused-template"

        response = test_client.get(
            f"/api/projects/{project_id}/prompts/{prompt_id}/analytics"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prompt_id"] == prompt_id
        assert data["total_executions"] == 0
        assert data["total_cost_usd"] == 0.0
        assert data["avg_latency_ms"] == 0.0
        assert data["total_tokens_in"] == 0
        assert data["total_tokens_out"] == 0

    def test_template_analytics_with_usage(self, test_project, test_client, override_auth_dependencies):
        """Test analytics aggregation for used template"""
        project_id, _, _ = test_project
        prompt_id = "analytics-test-template"
        session_id = str(uuid4())

        # Create multiple executions using the same template
        executions_data = [
            {"tokens_in": 10, "tokens_out": 20, "cost_usd": 0.001, "latency_ms": 100},
            {"tokens_in": 15, "tokens_out": 25, "cost_usd": 0.002, "latency_ms": 200},
            {"tokens_in": 20, "tokens_out": 30, "cost_usd": 0.003, "latency_ms": 300},
        ]

        for exec_data in executions_data:
            test_client.post(
                f"/api/projects/{project_id}/executions",
                json={
                    "trace_id": str(uuid4()),
                    "session_id": session_id,
                    "template_usages": [
                        {"prompt_id": prompt_id, "version": "1.0.0", "inputs": {}}
                    ],
                    "provider": "openai",
                    "model": "gpt-4",
                    **exec_data,
                },
            )

        # Get analytics
        response = test_client.get(
            f"/api/projects/{project_id}/prompts/{prompt_id}/analytics"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prompt_id"] == prompt_id
        assert data["total_executions"] == 3
        assert data["total_cost_usd"] == pytest.approx(0.006, rel=1e-9)
        assert data["avg_latency_ms"] == pytest.approx(200.0, rel=1e-9)
        assert data["total_tokens_in"] == 45  # 10 + 15 + 20
        assert data["total_tokens_out"] == 75  # 20 + 25 + 30

    def test_template_analytics_multiple_versions(self, test_project, test_client, override_auth_dependencies):
        """Test that analytics include all versions of a template"""
        project_id, _, _ = test_project
        prompt_id = "multi-version-template"
        session_id = str(uuid4())

        # Create executions with different versions
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": str(uuid4()),
                "session_id": session_id,
                "template_usages": [
                    {"prompt_id": prompt_id, "version": "1.0.0", "inputs": {}}
                ],
                "tokens_in": 10,
                "tokens_out": 20,
                "cost_usd": 0.001,
            },
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": str(uuid4()),
                "session_id": session_id,
                "template_usages": [
                    {"prompt_id": prompt_id, "version": "2.0.0", "inputs": {}}
                ],
                "tokens_in": 15,
                "tokens_out": 25,
                "cost_usd": 0.002,
            },
        )

        # Get analytics
        response = test_client.get(
            f"/api/projects/{project_id}/prompts/{prompt_id}/analytics"
        )

        assert response.status_code == 200
        data = response.json()

        # Should aggregate across all versions
        assert data["total_executions"] == 2
        assert data["total_tokens_in"] == 25
        assert data["total_tokens_out"] == 45

    def test_template_analytics_unauthorized(self, test_project, test_client):
        """Test analytics endpoint without authentication"""
        project_id, _, _ = test_project
        prompt_id = "test-template"

        response = test_client.get(
            f"/api/projects/{project_id}/prompts/{prompt_id}/analytics"
        )

        assert response.status_code == 401
