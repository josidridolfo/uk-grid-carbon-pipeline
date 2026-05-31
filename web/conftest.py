"""
pytest-django configuration for the energy-project web service.

This conftest is at the web/ root, so pytest discovers it automatically
when run from web/ or via `pytest web/` from the repo root.
"""

import django
import pytest


def pytest_configure(config):
    """Set Django settings module before Django is set up."""
    import os

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uk_grid_site.settings")
    os.environ.setdefault(
        "DJANGO_SECRET_KEY",
        "test-only-insecure-key-do-not-use-in-production-ever",
    )
    os.environ.setdefault(
        "DATABASE_URL",
        "sqlite://:memory:",
    )


@pytest.fixture(scope="session")
def django_db_setup():
    """
    Use SQLite in-memory for tests. No Snowflake or Postgres required.
    Phase 1c views make zero DB queries; this fixture exists so that
    @pytest.mark.django_db tests can run without a real Postgres container.
    """
    pass
