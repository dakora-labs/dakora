"""Tests for the prompt validation API."""

from __future__ import annotations

from sqlalchemy import insert

from dakora_server.core.database import prompt_parts_table


def test_validate_template_success(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": "Hello {{ name }}!",
            "declared_variables": ["name"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["errors"] == []
    assert data["variables_missing"] == []
    assert data["variables_unused"] == []


def test_validate_template_reports_syntax_error(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": "Hello {{ name ",
            "declared_variables": ["name"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert any(err["type"] == "syntax" for err in data["errors"])


def test_validate_template_detects_missing_and_unused_variables(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": "Weather in {{ city }}",
            "declared_variables": ["name"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["variables_missing"] == ["city"]
    assert data["variables_unused"] == ["name"]


def test_validate_template_missing_include_reports_error(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": '{% include "snippets/unknown" %}',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert any(err["type"] == "include" for err in data["errors"])


def test_validate_template_resolves_existing_include(
    test_project,
    test_client,
    db_connection,
    override_auth_dependencies,
):
    project_id, _, _ = test_project

    db_connection.execute(
        insert(prompt_parts_table).values(
            project_id=project_id,
            part_id="footer",
            category="snippets",
            name="snippets/footer",
            description="Test footer",
            content="-- footer --",
        )
    )
    db_connection.commit()

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": 'Body {% include "snippets/footer" %}',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["errors"] == []


def test_validate_template_detects_unmatched_closing_brace(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": "{name}}",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert any(err["type"] == "brace" for err in data["errors"])


def test_validate_template_detects_missing_closing_brace(test_project, test_client, override_auth_dependencies):
    project_id, _, _ = test_project

    response = test_client.post(
        f"/api/projects/{project_id}/prompts/validate",
        json={
            "template": "{{format_style",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert any(err["type"] == "brace" for err in data["errors"])
