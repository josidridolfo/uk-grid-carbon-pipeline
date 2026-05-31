"""Smoke tests for the Carbon Intensity API ingestion.

These are intentionally light: the contract here is "the API returns parseable JSON
and our asset turns it into a DataFrame with the expected columns." Integration
tests against live APIs are flaky — use sparingly and tolerate failures gracefully.
"""

from __future__ import annotations

import pandas as pd
import pytest

from uk_grid.assets.carbon_intensity import raw_carbon_intensity__national


@pytest.mark.integration
def test_raw_carbon_intensity__national_returns_dataframe() -> None:
    """Smoke test: the asset should return a non-empty DataFrame with expected schema."""
    from dagster import build_asset_context

    context = build_asset_context()
    df = raw_carbon_intensity__national(context)

    assert isinstance(df, pd.DataFrame), "Asset must return a pandas DataFrame"
    assert len(df) > 0, "API should return at least one half-hour interval"

    expected_columns = {
        "interval_start_utc",
        "interval_end_utc",
        "intensity_forecast_gco2_per_kwh",
        "intensity_actual_gco2_per_kwh",
        "index_band",
        "_fetched_at_utc",
    }
    assert expected_columns.issubset(set(df.columns)), (
        f"Missing columns: {expected_columns - set(df.columns)}"
    )
