"""Integration tests for optimization API endpoints."""

import pytest
from uuid import UUID
from unittest.mock import patch

from dakora_server.core.database import optimization_runs_table
from sqlalchemy import select


@pytest.mark.integration
class TestOptimizationAPI:
    """Test optimization endpoints."""

    def test_optimize_prompt_quota_check(
        self, test_project, test_client, override_auth_dependencies, db_connection
    ):
        """Test that optimization quota is checked before running optimization."""
        project_id, workspace_id, _ = test_project

        # Create a simple prompt first
        prompt_data = {
            "id": "test-greeting",
            "version": "1.0.0",
            "template": "Hello {{ name }}!",
            "inputs": {
                "name": {"type": "string", "required": True}
            },
        }
        create_response = test_client.post(
            f"/api/projects/{project_id}/prompts", json=prompt_data
        )
        assert create_response.status_code == 201

        # Create quota record with exceeded limit (free tier = 10)
        from dakora_server.core.database import workspace_quotas_table
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        db_connection.execute(
            pg_insert(workspace_quotas_table).values(
                workspace_id=workspace_id,
                tier="free",
                tokens_used_month=0,
                optimization_runs_used_month=10,  # Set to limit
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            ).on_conflict_do_update(
                index_elements=["workspace_id"],
                set_={"optimization_runs_used_month": 10}
            )
        )
        db_connection.commit()

        # Try to optimize - should fail with quota exceeded
        response = test_client.post(
            f"/api/projects/{project_id}/prompts/test-greeting/optimize",
            json={"test_cases": None},
        )

        assert response.status_code == 429
        assert "quota exceeded" in response.json()["detail"].lower()

    def test_get_optimization_runs_empty(
        self, test_project, test_client, override_auth_dependencies
    ):
        """Test getting optimization runs when none exist."""
        project_id, _, _ = test_project

        # Create a prompt
        prompt_data = {
            "id": "test-prompt",
            "version": "1.0.0",
            "template": "Test template",
            "inputs": {},
        }
        create_response = test_client.post(
            f"/api/projects/{project_id}/prompts", json=prompt_data
        )
        assert create_response.status_code == 201

        # Get optimization runs
        response = test_client.get(
            f"/api/projects/{project_id}/prompts/test-prompt/optimization-runs"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["optimization_runs"] == []
        assert data["total"] == 0

    def test_optimization_run_cleanup(
        self, test_project, db_connection
    ):
        """Test that only 10 optimization runs are kept per prompt (FIFO)."""
        from sqlalchemy import insert
        from datetime import datetime, timedelta, timezone

        project_id, workspace_id, owner_id = test_project

        # Create 12 optimization runs
        base_time = datetime.now(timezone.utc)
        for i in range(12):
            db_connection.execute(
                insert(optimization_runs_table).values(
                    project_id=project_id,
                    prompt_id="test-prompt",
                    version="1.0.0",
                    original_template="Original",
                    optimized_template=f"Optimized {i}",
                    insights=[],
                    token_reduction_pct=10.0,
                    applied=0,
                    user_id=str(owner_id),  # user_id is String(255) in schema
                    workspace_id=workspace_id,
                    created_at=base_time + timedelta(minutes=i),
                )
            )
        db_connection.commit()

        # Verify all 12 were created
        result = db_connection.execute(
            select(optimization_runs_table).where(
                optimization_runs_table.c.project_id == project_id,
                optimization_runs_table.c.prompt_id == "test-prompt",
            )
        )
        assert len(result.fetchall()) == 12

    def test_get_workspace_quota(
        self, test_project, test_client, db_connection
    ):
        """Test getting workspace quota information."""
        _, workspace_id, _ = test_project

        # Get quota info
        response = test_client.get(f"/api/workspaces/{workspace_id}/quota")

        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert "optimizations_used" in data
        assert "optimizations_limit" in data
        assert "optimizations_remaining" in data
        assert "usage_percentage" in data
        assert "period_start" in data
        assert "period_end" in data

        # Verify initial state
        assert data["tier"] == "free"
        assert data["optimizations_used"] == 0
        assert data["optimizations_limit"] == 10  # Default free tier
        assert data["optimizations_remaining"] == 10