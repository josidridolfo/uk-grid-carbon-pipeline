"""Smoke tests for the Carbon Intensity API ingestion.

These are intentionally light: the contract here is "the API returns parseable JSON
and our asset turns it into a DataFrame with the expected columns." Integration
tests against live APIs are flaky — use sparingly and tolerate failures gracefully.
"""

from __future__ import annotations

import pandas as pd
import pytest

from uk_grid.assets.carbon_intensity import (
    raw_carbon_intensity__national,
    raw_carbon_intensity__regional,
)


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


@pytest.mark.integration
def test_raw_carbon_intensity__regional_returns_18_regions_per_interval() -> None:
    """Live API integration smoke test: the regional endpoint returns 18
    regions per interval; the asset flattens to one row per (region, interval).
    For a trailing-24h pull, expect ~48 intervals x 18 regions = ~864 rows.
    """
    from dagster import build_asset_context

    context = build_asset_context()
    df = raw_carbon_intensity__regional(context)

    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0, "API should return data for the trailing 24h"

    # Each interval should have 17-18 regions (occasionally one is missing
    # on the API edges; allow both)
    region_counts = df.groupby("interval_start_utc").size()
    assert region_counts.between(17, 18).all(), (
        f"Each interval should have 17-18 regions; got {region_counts.unique()}"
    )

    expected_columns = {
        "interval_start_utc",
        "interval_end_utc",
        "region_id",
        "region_shortname",
        "region_dnoregion",
        "intensity_forecast_gco2_per_kwh",
        "intensity_actual_gco2_per_kwh",
        "index_band",
        "_fetched_at_utc",
    }
    assert expected_columns.issubset(set(df.columns))

    # All 14 DNO regions should be present (15-18 are aggregates, may or
    # may not all be returned)
    assert set(df["region_id"].unique()) >= set(range(1, 15))
