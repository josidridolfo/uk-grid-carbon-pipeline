"""
Snowflake connection helper for the energy-project web service.

This module is imported and called at REQUEST TIME only — never at module import
time, never during settings initialisation, and never in management commands
that don't need data. This keeps local dev (and dbt parse CI runs) free of
Snowflake credential requirements.

Phase 1c: wires the config and validates it. Actual queries live in Phase 2.

Role assumption: always connects as REPORTER (read-only on ANALYTICS_MARTS).
Never use TRANSFORMER or LOADER from this service.
"""

import snowflake.connector
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_snowflake_connection() -> snowflake.connector.SnowflakeConnection:
    """
    Return an open Snowflake connection using SNOWFLAKE_CONFIG from Django settings.

    The caller is responsible for closing the connection (use as a context manager
    or call .close() explicitly). Example::

        with get_snowflake_connection() as conn:
            cursor = conn.cursor(snowflake.connector.DictCursor)
            cursor.execute("SELECT ...")
            rows = cursor.fetchall()

    Raises
    ------
    ImproperlyConfigured
        If any required Snowflake setting (account, user, password) is None or empty.
        This surfaces a clear error rather than a misleading auth failure from the driver.
    """
    cfg = getattr(settings, "SNOWFLAKE_CONFIG", {})

    required_fields = ("account", "user", "password")
    missing = [f for f in required_fields if not cfg.get(f)]
    if missing:
        raise ImproperlyConfigured(
            f"SNOWFLAKE_CONFIG is missing required field(s): {', '.join(missing)}. "
            "Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, and SNOWFLAKE_PASSWORD in your "
            "environment or .env file."
        )

    return snowflake.connector.connect(
        account=cfg["account"],
        user=cfg["user"],
        password=cfg["password"],
        role=cfg.get("role", "REPORTER"),
        warehouse=cfg.get("warehouse", "ENERGY_WH"),
        database=cfg.get("database", "UK_GRID"),
        schema=cfg.get("schema", "ANALYTICS_MARTS"),
        # Ensure results arrive as Python-native types, not Decimal/etc.
        numpy=False,
    )
