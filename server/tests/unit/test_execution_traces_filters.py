"""Focused tests for execution list filters and marker stripping.

These are lightweight checks to boost coverage on:
- Query validation (start/end ordering)
- Limit precedence when both limit and page_size are provided
- Marker stripping helper for template markers in message parts
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_list_executions_end_before_start_returns_400(test_client, override_auth_dependencies, test_project):
    project_id, _, _ = test_project

    start = datetime.now(timezone.utc)
    end = start - timedelta(days=1)

    resp = test_client.get(
        f"/api/projects/{project_id}/executions",
        params={
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )
    assert resp.status_code == 400


def test_limit_overridden_by_page_size(test_client, override_auth_dependencies, test_project):
    project_id, _, _ = test_project

    resp = test_client.get(
        f"/api/projects/{project_id}/executions",
        params={
            "limit": 5,
            "page_size": 7,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    # Response echoes effective limit used by the endpoint
    assert data["limit"] == 7


def test_strip_dakora_markers_strips_and_trims():
    from dakora_server.api.execution_traces import _strip_dakora_markers

    parts = [
        {
            "type": "text",
            "content": "<!--dakora:prompt_id=abc,version=1.2.3-->\n  Hello world  ",
        },
        {"type": "image", "url": "http://example.com"},
    ]

    cleaned = _strip_dakora_markers(parts)
    assert cleaned[0]["content"] == "Hello world"
    # Non-text parts untouched
    assert cleaned[1]["url"] == "http://example.com"

