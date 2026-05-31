"""
Tests for apps.core views.

Run with: cd web && pytest apps/core/tests.py -v
Or via the full suite: cd web && pytest

These tests use pytest-django's `client` fixture and do NOT require a live
Snowflake connection or real database rows — Phase 1c views are deliberately
query-free.
"""

import json

import pytest


@pytest.mark.django_db
def test_home_returns_200_with_title(client):
    """Home page should load successfully and include the site identity string."""
    response = client.get("/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "energy-project" in content.lower() or "UK Grid" in content


@pytest.mark.django_db
def test_health_returns_json_ok(client):
    """Health endpoint must return 200 with status=ok JSON payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    data = json.loads(response.content)
    assert data["status"] == "ok"
    assert data["service"] == "energy-project"
    assert "git_sha" in data


@pytest.mark.django_db
def test_home_template_is_used(client):
    """Home view must render core/home.html (extends base.html)."""
    response = client.get("/")
    assert response.status_code == 200
    template_names = [t.name for t in response.templates]
    assert "core/home.html" in template_names


@pytest.mark.django_db
def test_home_context_contains_now_utc(client):
    """HomeView injects now_utc into context for display in the template."""
    from datetime import timezone

    response = client.get("/")
    assert response.status_code == 200
    now_utc = response.context.get("now_utc")
    assert now_utc is not None
    assert now_utc.tzinfo == timezone.utc


@pytest.mark.django_db
def test_health_no_db_queries(client, django_assert_num_queries):
    """Health endpoint must not touch the database (fast liveness probe)."""
    with django_assert_num_queries(0):
        response = client.get("/health")
    assert response.status_code == 200
