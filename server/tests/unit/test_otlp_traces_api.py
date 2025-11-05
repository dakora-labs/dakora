"""Unit tests for OTLP trace ingestion API (/api/v1/traces).

Covers JSON ingest success, invalid content types, invalid/empty payloads,
and auth context without project scope. Uses dependency overrides and
monkeypatching to avoid exercising heavy DB logic.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest


def _sample_span(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base = {
        "trace_id": "0123456789abcdef0123456789abcdef",
        "span_id": "0123456789abcdef",
        "parent_span_id": None,
        "span_name": "chat",
        "span_kind": "INTERNAL",
        "attributes": {"gen_ai.operation.name": "chat"},
        "events": [],
        "start_time_ns": 1_000_000_000,
        "end_time_ns": 2_000_000_000,
        "status_code": "OK",
        "status_message": None,
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.mark.integration
def test_ingest_json_success(test_client, override_auth_dependencies, monkeypatch):
    """Happy path: JSON content parses and returns stats from processor."""
    spans_payload = {"spans": [_sample_span(), _sample_span({"span_id": "feedfacecafebeef"})]}

    # Stub out the processor to avoid DB logic
    from dakora_server.core import otlp_processor as processor_mod

    def fake_process_trace_batch(spans, project_id, conn):
        # Validate spans are Pydantic models with required fields
        assert len(spans) == 2
        assert hasattr(spans[0], "trace_id")
        return {"spans_stored": len(spans), "executions_created": 1, "recomputes": 0}

    monkeypatch.setattr(processor_mod, "process_trace_batch", fake_process_trace_batch)

    # Execute
    resp = test_client.post(
        "/api/v1/traces",
        json=spans_payload,
        headers={"Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["spans_ingested"] == 2
    assert "created 1 execution" in data["message"]


def test_ingest_invalid_content_type_415(test_client, override_auth_dependencies):
    """Unsupported Content-Type should return 415."""
    resp = test_client.post(
        "/api/v1/traces",
        data="not protobuf or json",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 415


def test_ingest_invalid_json_400(test_client, override_auth_dependencies):
    """Invalid JSON payload should return 400 with a parse error message."""
    resp = test_client.post(
        "/api/v1/traces",
        data="{ this is not valid json }",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_ingest_empty_spans_400(test_client, override_auth_dependencies):
    """Empty spans array should return 400."""
    resp = test_client.post(
        "/api/v1/traces",
        json={"spans": []},
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "No spans provided"


def test_ingest_missing_project_scope_401(test_client, monkeypatch):
    """AuthContext without project_id should trigger 401 project-scope requirement."""
    from dakora_server.main import app
    from dakora_server.auth import get_auth_context, AuthContext

    async def fake_auth_ctx():
        # Simulate authenticated user but without project scope
        return AuthContext(user_id=str(uuid4()), project_id=None, auth_method="test")

    app.dependency_overrides[get_auth_context] = fake_auth_ctx
    try:
        resp = test_client.post(
            "/api/v1/traces",
            json={"spans": [_sample_span()]},
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401
        assert "project scope" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()

