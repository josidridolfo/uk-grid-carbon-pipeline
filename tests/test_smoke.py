"""Smoke tests — credential-free, network-free, runs in every PR's CI.

These guard against import-level regressions: package not installable,
asset modules not loadable, Dagster definitions object failing to construct,
etc. The full set of business-logic unit tests lives in Phase 3 once
pure functions are extracted from the asset code.
"""

from __future__ import annotations


def test_uk_grid_package_imports() -> None:
    """The editable install resolves; the package is importable as `uk_grid`."""
    import uk_grid

    assert uk_grid.__file__ is not None


def test_definitions_module_loads() -> None:
    """All Dagster assets are registered without errors at import time."""
    from uk_grid import definitions

    assert hasattr(definitions, "defs")
    assert hasattr(definitions, "all_assets")
    assert len(definitions.all_assets) >= 5


def test_settings_class_loads_with_defaults() -> None:
    """The Settings class instantiates from env/defaults without raising."""
    from uk_grid.resources import Settings

    s = Settings()
    assert s.snowflake_role
    assert s.snowflake_warehouse
    assert s.snowflake_database


def test_custom_io_manager_class_exists() -> None:
    """The custom IOManager subclass is exposed and constructs from settings."""
    from uk_grid.resources import UKGridSnowflakeIOManager, settings

    mgr = UKGridSnowflakeIOManager(settings)
    assert mgr._settings is settings
