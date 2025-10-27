"""Integration tests for trace telemetry API endpoints.

This test suite covers the trace-based execution logging system
for observability from MAF middleware.
"""

from datetime import datetime
from uuid import uuid4

import pytest


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
                "source": "maf",
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
                        "metadata": {"stage": "prompt"},
                        "role": "system",
                        "source": "instruction",
                        "message_index": -1,
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
                        "role": "system",
                        "source": "instruction",
                        "message_index": -1,
                    },
                    {
                        "prompt_id": "user-query",
                        "version": "2.1.0",
                        "inputs": {"query": "What is AI?"},
                        "role": "user",
                        "source": "message",
                        "message_index": 1
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

    @staticmethod
    def _parse_response(response):
        data = response.json()
        assert isinstance(data, dict)
        assert "executions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        return data

    def test_list_executions_empty(self, test_project, test_client, override_auth_dependencies):
        """Test listing executions with a filter that yields no results"""
        project_id, _, _ = test_project
        missing_session_id = str(uuid4())

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": missing_session_id},
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        assert data["executions"] == []
        assert data["total"] == 0
        assert data["limit"] == 25  # default page size
        assert data["offset"] == 0

    def test_list_executions_with_data(self, test_project, test_client, override_auth_dependencies):
        """Test listing executions after creating some"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

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
                    "source": "maf",
                },
            )

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id, "limit": 10},
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        executions = data["executions"]

        assert len(executions) == 3
        assert data["total"] == 3
        assert data["limit"] == 10
        assert data["offset"] == 0

        returned_ids = {execution["trace_id"] for execution in executions}
        assert returned_ids == set(trace_ids)

        for execution in executions:
            assert execution["session_id"] == session_id
            assert execution["provider"] == "openai"
            assert execution["model"] == "gpt-4"
            assert execution["template_count"] == 0
            assert execution.get("source") == "maf"

    def test_list_executions_filter_by_session(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by session_id"""
        project_id, _, _ = test_project
        session_id_1 = str(uuid4())
        session_id_2 = str(uuid4())

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

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id_1},
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        executions = data["executions"]

        matching = [entry for entry in executions if entry["trace_id"] == trace_1]
        assert len(matching) == 1
        assert matching[0]["session_id"] == session_id_1
        assert data["total"] == 1

    def test_list_executions_filter_by_agent(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by agent_id"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

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

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"agent_id": "agent-A", "session_id": session_id},
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        executions = data["executions"]

        matching = [entry for entry in executions if entry["trace_id"] == trace_1]
        assert len(matching) == 1
        assert matching[0]["agent_id"] == "agent-A"
        assert data["total"] == 1

    def test_list_executions_filter_by_prompt(self, test_project, test_client, override_auth_dependencies):
        """Test filtering executions by prompt_id"""
        project_id, _, _ = test_project
        session_id = str(uuid4())
        prompt_id = "test-prompt"

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

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"prompt_id": prompt_id, "session_id": session_id},
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        executions = data["executions"]

        matching = [entry for entry in executions if entry["trace_id"] == trace_1]
        assert len(matching) == 1
        assert matching[0]["template_count"] == 1
        assert data["total"] == 1

    def test_list_executions_pagination(self, test_project, test_client, override_auth_dependencies):
        """Test pagination of execution list"""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        created_ids = []
        for _ in range(5):
            trace_id = str(uuid4())
            created_ids.append(trace_id)
            test_client.post(
                f"/api/projects/{project_id}/executions",
                json={"trace_id": trace_id, "session_id": session_id},
            )

        response_page_one = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"limit": 2, "session_id": session_id},
        )

        assert response_page_one.status_code == 200
        data_page_one = self._parse_response(response_page_one)
        assert len(data_page_one["executions"]) == 2
        assert data_page_one["limit"] == 2
        assert data_page_one["offset"] == 0
        assert data_page_one["total"] == 5

        response_page_two = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"limit": 2, "offset": 2, "session_id": session_id},
        )

        assert response_page_two.status_code == 200
        data_page_two = self._parse_response(response_page_two)
        assert len(data_page_two["executions"]) == 2
        assert data_page_two["offset"] == 2
        assert data_page_two["total"] == 5
        returned_ids = {entry["trace_id"] for entry in data_page_two["executions"]}
        assert returned_ids.issubset(set(created_ids))

    def test_list_executions_filter_by_provider_model_and_cost(self, test_project, test_client, override_auth_dependencies):
        """Ensure provider, model, and min_cost filters work together."""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        trace_openai_low = str(uuid4())
        trace_azure_mid = str(uuid4())
        trace_openai_high = str(uuid4())

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_openai_low,
                "session_id": session_id,
                "provider": "openai",
                "model": "gpt-4-turbo",
                "cost_usd": 0.001,
            },
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_azure_mid,
                "session_id": session_id,
                "provider": "azure_openai",
                "model": "gpt-4o",
                "cost_usd": 0.05,
            },
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": trace_openai_high,
                "session_id": session_id,
                "provider": "openai",
                "model": "gpt-4o-mini",
                "cost_usd": 0.25,
            },
        )

        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={
                "provider": "OpenAI",
                "model": "4o",
                "min_cost": 0.1,
                "session_id": session_id,
            },
        )

        assert response.status_code == 200
        data = self._parse_response(response)
        executions = data["executions"]

        assert len(executions) == 1
        assert executions[0]["trace_id"] == trace_openai_high
        assert executions[0]["provider"] == "openai"
        assert executions[0]["model"] == "gpt-4o-mini"
        assert data["total"] == 1

    def test_list_executions_has_templates_toggle(self, test_project, test_client, override_auth_dependencies):
        """Verify has_templates filter includes or excludes linked templates."""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        template_trace = str(uuid4())
        no_template_trace = str(uuid4())

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": template_trace,
                "session_id": session_id,
                "template_usages": [
                    {"prompt_id": "prompt-one", "version": "1.0.0", "inputs": {}}
                ],
            },
        )

        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={
                "trace_id": no_template_trace,
                "session_id": session_id,
            },
        )

        response_has_templates = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"has_templates": True, "session_id": session_id},
        )
        assert response_has_templates.status_code == 200
        data_has_templates = self._parse_response(response_has_templates)
        assert {entry["trace_id"] for entry in data_has_templates["executions"]} == {template_trace}
        assert data_has_templates["executions"][0]["template_count"] == 1
        assert data_has_templates["total"] == 1

        response_no_templates = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"has_templates": False, "session_id": session_id},
        )
        assert response_no_templates.status_code == 200
        data_no_templates = self._parse_response(response_no_templates)
        assert {entry["trace_id"] for entry in data_no_templates["executions"]} == {no_template_trace}
        assert data_no_templates["executions"][0]["template_count"] == 0
        assert data_no_templates["total"] == 1

    def test_list_executions_date_range_filters(self, test_project, test_client, override_auth_dependencies):
        """Ensure start/end filters respect created_at timestamps."""
        project_id, _, _ = test_project
        session_id = str(uuid4())

        early_trace = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": early_trace, "session_id": session_id},
        )

        midpoint = datetime.utcnow().isoformat()

        late_trace = str(uuid4())
        test_client.post(
            f"/api/projects/{project_id}/executions",
            json={"trace_id": late_trace, "session_id": session_id},
        )

        response_start = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id, "start": midpoint},
        )
        assert response_start.status_code == 200
        data_start = self._parse_response(response_start)
        assert {entry["trace_id"] for entry in data_start["executions"]} == {late_trace}
        assert data_start["total"] == 1

        response_end = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id, "end": midpoint},
        )
        assert response_end.status_code == 200
        data_end = self._parse_response(response_end)
        assert {entry["trace_id"] for entry in data_end["executions"]} == {early_trace}
        assert data_end["total"] == 1

    def test_list_executions_pagination_with_page_params(self, test_project, test_client, override_auth_dependencies):
        """Verify page/page_size parameters translate to correct offset."""
        project_id, _, _ = test_project
        session_id = str(uuid4())
        trace_ids = []

        for _ in range(3):
            trace_id = str(uuid4())
            trace_ids.append(trace_id)
            test_client.post(
                f"/api/projects/{project_id}/executions",
                json={"trace_id": trace_id, "session_id": session_id},
            )

        response_page_two = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id, "page": 2, "page_size": 1},
        )
        assert response_page_two.status_code == 200
        data_page_two = self._parse_response(response_page_two)
        assert len(data_page_two["executions"]) == 1
        assert data_page_two["limit"] == 1
        assert data_page_two["offset"] == 1
        assert data_page_two["total"] == 3
        assert data_page_two["executions"][0]["trace_id"] in set(trace_ids)

        response_page_three = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"session_id": session_id, "page": 3, "page_size": 1},
        )
        assert response_page_three.status_code == 200
        data_page_three = self._parse_response(response_page_three)
        assert len(data_page_three["executions"]) == 1
        assert data_page_three["offset"] == 2

    def test_list_executions_invalid_date_range(self, test_project, test_client, override_auth_dependencies):
        """Invalid date range should yield 400."""
        project_id, _, _ = test_project
        response = test_client.get(
            f"/api/projects/{project_id}/executions",
            params={"start": "2024-01-02T00:00:00", "end": "2024-01-01T00:00:00"},
        )
        assert response.status_code == 400


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
                "source": "maf",
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
        assert data["source"] == "maf"
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
                "metadata": {"phase": "system"},
                "role": "system",
                "source": "instruction",
                "message_index": -1,
            },
            {
                "prompt_id": "farewell",
                "version": "1.2.0",
                "inputs": {"name": "Bob"},
                "metadata": {"phase": "user"},
                "role": "user",
                "source": "message",
                "message_index": 0,
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
        assert data["templates_used"][0]["metadata"] == {"phase": "system"}
        assert data["templates_used"][0]["role"] == "system"
        assert data["templates_used"][0]["source"] == "instruction"
        assert data["templates_used"][0]["message_index"] == -1

        assert data["templates_used"][1]["prompt_id"] == "farewell"
        assert data["templates_used"][1]["version"] == "1.2.0"
        assert data["templates_used"][1]["position"] == 1
        assert data["templates_used"][1]["metadata"] == {"phase": "user"}
        assert data["templates_used"][1]["role"] == "user"
        assert data["templates_used"][1]["source"] == "message"
        assert data["templates_used"][1]["message_index"] == 0

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
