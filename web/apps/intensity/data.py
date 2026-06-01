"""
Snowflake data-access layer for apps.intensity.

Deliberately isolated from views and charts so each layer is independently
testable. Views import fetch_national_intensity_rows; tests patch it.

Query design decisions:
  - Aggregation happens in Snowflake, not Python — never pull raw rows.
  - Parameterised with DATEADD rather than formatting dates in Python.
  - DictCursor returns column-name-keyed dicts, matching the chart contract.
  - Connection opened and closed within the function; no connection pooling
    at this traffic level. Add pool in a later phase if latency spikes.
"""

from __future__ import annotations

import logging

import snowflake.connector

from apps.core.snowflake import get_snowflake_connection

logger = logging.getLogger(__name__)

_NATIONAL_INTENSITY_SQL = """
SELECT
    hour_start_utc,
    mean_intensity_actual_gco2_per_kwh,
    mean_intensity_forecast_gco2_per_kwh
FROM ANALYTICS_MARTS.FACT_CARBON_INTENSITY_HOURLY
WHERE hour_start_utc >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
ORDER BY hour_start_utc ASC
"""


def fetch_national_intensity_rows() -> list[dict]:
    """
    Query the last 24 hours of national carbon intensity data from Snowflake.

    Returns
    -------
    list[dict]
        Each dict has keys matching the SELECT columns (lowercase):
          - hour_start_utc
          - mean_intensity_actual_gco2_per_kwh
          - mean_intensity_forecast_gco2_per_kwh

    Raises
    ------
    snowflake.connector.errors.DatabaseError
        Propagated to caller (view handles by serving stale cache or error page).
    django.core.exceptions.ImproperlyConfigured
        If Snowflake credentials are missing from settings.
    """
    logger.debug("Querying Snowflake: national intensity last 24h")
    with get_snowflake_connection() as conn:
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute(_NATIONAL_INTENSITY_SQL)
        rows = cursor.fetchall()

    # Normalise column names to lowercase to be consistent regardless of
    # Snowflake's default UPPERCASE_COLUMN_NAMES behaviour.
    normalised = [
        {k.lower(): v for k, v in row.items()}
        for row in rows
    ]
    logger.debug("Fetched %d rows from Snowflake", len(normalised))
    return normalised
