"""Integration tests for prompt execution API endpoints"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from dakora_server.core.llm.provider import ExecutionResult, ModelInfo


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execute_prompt_success(
    test_client, test_engine, setup_test_data, mock_provider, auth_override
):
    """Test successful prompt execution"""
    from dakora_server.main import app

    user_id, workspace_id, project_id = setup_test_data

    # Create a test prompt
    from dakora_server.core.database import prompts_table, get_connection
    from sqlalchemy import insert, select
    from uuid import UUID

    prompt_id = "test-greeting"

    with get_connection(test_engine) as conn:
        conn.execute(
            insert(prompts_table).values(
                project_id=UUID(project_id),
                prompt_id=prompt_id,
                version="1.0.0",
                description="Test prompt",
                storage_path=f"projects/{project_id}/prompts/{prompt_id}.yaml",
            )
        )

    # Mock vault to return template
    mock_vault = MagicMock()
    mock_template = MagicMock()
    mock_template.version = "1.0.0"
    mock_template.template = "Hello {{ name }}!"
    mock_vault.get.return_value = mock_template

    # Mock renderer
    mock_renderer = MagicMock()
    mock_renderer.render.return_value = "Hello Alice!"

    # Mock provider execution
    mock_result = ExecutionResult(
        content="Hello Alice! How are you today?",
        tokens_input=10,
        tokens_output=20,
        tokens_total=30,
        cost_usd=0.0015,
        latency_ms=500,
        model="gpt-4o",
        provider="azure_openai",
    )
    mock_provider.execute = AsyncMock(return_value=mock_result)

    # Use dependency overrides for injected dependencies and patches for direct instantiations
    from dakora_server.auth import get_project_vault

    mock_registry = MagicMock()
    mock_registry.get_provider_by_name.return_value = mock_provider

    # Override get_project_vault (injected dependency)
    app.dependency_overrides[get_project_vault] = lambda: mock_vault

    try:
        # Patch Renderer and ProviderRegistry (direct instantiations, not dependencies)
        with patch("dakora_server.api.project_executions.Renderer", return_value=mock_renderer):
            with patch("dakora_server.api.project_executions.ProviderRegistry", return_value=mock_registry):
                response = test_client.post(
                    f"/api/projects/{project_id}/prompts/{prompt_id}/execute",
                    json={"inputs": {"name": "Alice"}, "provider": "azure_openai", "model": "gpt-4o"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "execution_id" in data
                assert data["trace_id"]
                assert data["content"] == "Hello Alice! How are you today?"
                assert data["metrics"]["tokens_total"] == 30
                assert data["metrics"]["cost_usd"] == 0.0015
                assert data["model"] == "gpt-4o"
                assert data["provider"] == "azure_openai"

                from dakora_server.core.database import prompt_executions_table, get_connection

                with get_connection(test_engine) as conn:
                    stored = conn.execute(
                        select(prompt_executions_table.c.trace_id)
                        .where(
                            prompt_executions_table.c.project_id == UUID(project_id),
                            prompt_executions_table.c.prompt_id == prompt_id,
                        )
                        .order_by(prompt_executions_table.c.created_at.desc())
                        .limit(1)
                    ).fetchone()

                assert stored is not None
                assert stored.trace_id == data["trace_id"]
    finally:
        # Clear overrides
        app.dependency_overrides.pop(get_project_vault, None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execute_prompt_quota_exceeded(test_client, test_engine, setup_test_data, auth_override):
    """Test execution fails when quota is exceeded"""
    user_id, workspace_id, project_id = setup_test_data

    # Set quota to exceeded
    from dakora_server.core.database import workspace_quotas_table, get_connection
    from sqlalchemy import update
    from uuid import UUID

    with get_connection(test_engine) as conn:
        conn.execute(
            update(workspace_quotas_table)
            .where(workspace_quotas_table.c.workspace_id == UUID(workspace_id))
            .values(tokens_used_month=100_000)
        )

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/test-greeting/execute",
        json={"inputs": {"name": "Alice"}},
    )

    assert response.status_code == 429
    assert "quota exceeded" in response.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execute_prompt_not_found(test_client, setup_test_data, auth_override):
    """Test execution fails when prompt doesn't exist"""
    user_id, workspace_id, project_id = setup_test_data

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/nonexistent/execute",
        json={"inputs": {}},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_available_models(test_client, setup_test_data, mock_provider, auth_override):
    """Test fetching available models"""
    user_id, workspace_id, project_id = setup_test_data

    # Mock provider models
    mock_models = [
        ModelInfo(
            id="gpt-4o",
            name="GPT-4o",
            provider="azure_openai",
            input_cost_per_1k=0.005,
            output_cost_per_1k=0.015,
            max_tokens=128000,
        ),
        ModelInfo(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider="azure_openai",
            input_cost_per_1k=0.00015,
            output_cost_per_1k=0.0006,
            max_tokens=128000,
        ),
    ]

    # Use patches for ProviderRegistry (direct instantiation, not a dependency)
    mock_registry = MagicMock()
    mock_registry.get_all_models.return_value = mock_models

    with patch("dakora_server.api.project_executions.ProviderRegistry", return_value=mock_registry):
        response = test_client.get(
            f"/api/projects/{project_id}/models",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["models"]) == 2
        assert data["models"][0]["id"] == "gpt-4o"
        assert data["models"][1]["id"] == "gpt-4o-mini"
        assert data["default_model"] is None  # No default - user must select


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_execution_history(test_client, test_engine, setup_test_data, auth_override):
    """Test fetching execution history for a prompt"""
    user_id, workspace_id, project_id = setup_test_data

    # Create test executions
    from dakora_server.core.database import prompt_executions_table, get_connection
    from sqlalchemy import insert
    from uuid import UUID

    prompt_id = "test-greeting"

    with get_connection(test_engine) as conn:
        for i in range(3):
            conn.execute(
                insert(prompt_executions_table).values(
                    project_id=UUID(project_id),
                    prompt_id=prompt_id,
                    version="1.0.0",
                    trace_id=str(uuid4()),
                    inputs_json={"name": f"User{i}"},
                    model="gpt-4o",
                    provider="azure_openai",
                    output_text=f"Hello User{i}!",
                    error_message=None,
                    status="success",
                    tokens_input=10,
                    tokens_output=20,
                    tokens_total=30,
                    cost_usd=0.0015,
                    latency_ms=500,
                    user_id=user_id,
                    workspace_id=UUID(workspace_id),
                )
            )

    response = test_client.get(
        f"/api/projects/{project_id}/prompts/{prompt_id}/executions",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["executions"]) == 3
    assert data["executions"][0]["status"] == "success"
    assert data["executions"][0]["metrics"]["tokens_total"] == 30
    assert all(exec["trace_id"] for exec in data["executions"])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execution_cleanup_keeps_only_20(
    test_client, test_engine, setup_test_data, mock_provider, auth_override
):
    """Test that execution history is limited to 20 most recent"""
    user_id, workspace_id, project_id = setup_test_data

    # Create a test prompt
    from dakora_server.core.database import prompts_table, prompt_executions_table, get_connection
    from sqlalchemy import insert, select, func
    from uuid import UUID

    prompt_id = "test-cleanup"

    with get_connection(test_engine) as conn:
        conn.execute(
            insert(prompts_table).values(
                project_id=UUID(project_id),
                prompt_id=prompt_id,
                version="1.0.0",
                description="Test prompt",
                storage_path=f"projects/{project_id}/prompts/{prompt_id}.yaml",
            )
        )

        # Create 19 existing executions
        for i in range(19):
            conn.execute(
                insert(prompt_executions_table).values(
                    project_id=UUID(project_id),
                    prompt_id=prompt_id,
                    version="1.0.0",
                    inputs_json={"test": i},
                    model="gpt-4o",
                    provider="azure_openai",
                    output_text=f"Output {i}",
                    status="success",
                    tokens_input=10,
                    tokens_output=20,
                    tokens_total=30,
                    cost_usd=0.001,
                    latency_ms=100,
                    user_id=user_id,
                    workspace_id=UUID(workspace_id),
                )
            )

    # Mock vault and renderer
    mock_vault = MagicMock()
    mock_template = MagicMock()
    mock_template.version = "1.0.0"
    mock_template.template = "Test template"
    mock_vault.get.return_value = mock_template

    mock_renderer = MagicMock()
    mock_renderer.render.return_value = "Test"

    # Mock provider
    mock_result = ExecutionResult(
        content="Test output",
        tokens_input=10,
        tokens_output=20,
        tokens_total=30,
        cost_usd=0.001,
        latency_ms=100,
        model="gpt-4o",
        provider="azure_openai",
    )
    mock_provider.execute = AsyncMock(return_value=mock_result)

    # Use dependency overrides for injected dependencies and patches for direct instantiations
    from dakora_server.main import app
    from dakora_server.auth import get_project_vault

    mock_registry = MagicMock()
    mock_registry.get_provider_by_name.return_value = mock_provider

    # Override get_project_vault (injected dependency)
    app.dependency_overrides[get_project_vault] = lambda: mock_vault

    try:
        # Patch Renderer and ProviderRegistry (direct instantiations, not dependencies)
        with patch("dakora_server.api.project_executions.Renderer", return_value=mock_renderer):
            with patch("dakora_server.api.project_executions.ProviderRegistry", return_value=mock_registry):
                # Execute 2 more times (should trigger cleanup)
                for i in range(2):
                    response = test_client.post(
                        f"/api/projects/{project_id}/prompts/{prompt_id}/execute",
                        json={"inputs": {"test": i + 19}, "provider": "azure_openai", "model": "gpt-4o"},
                    )
                    assert response.status_code == 200
    finally:
        # Clear overrides
        app.dependency_overrides.pop(get_project_vault, None)

    # Verify total count is 20
    with get_connection(test_engine) as conn:
        count_result = conn.execute(
            select(func.count()).select_from(prompt_executions_table).where(
                prompt_executions_table.c.project_id == UUID(project_id),
                prompt_executions_table.c.prompt_id == prompt_id,
            )
        )
        total = count_result.scalar()

    assert total == 20
