"""Unit tests for `_parse_regional_rows` — the pure parser for the
Carbon Intensity API's `/regional/intensity/{from}/{to}` endpoint.

Fixture-driven TDD: tests/fixtures/regional_response.json was captured from
a real API response, trimmed to 2 intervals x 3 regions = 6 rows. The
regional endpoint returns ``forecast`` and ``index`` only (no ``actual`` —
unlike the national endpoint, regional intensity is model-derived and
Carbon Intensity API never settles it back). The parser preserves an
``intensity_actual_gco2_per_kwh`` column for schema-consistency with the
national parser; it will always be NaN until/unless the API changes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from uk_grid.assets.carbon_intensity import _parse_regional_rows

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "regional_response.json"
FIXED_FETCHED_AT = datetime(2026, 5, 31, 22, 0, tzinfo=UTC)


def _load_fixture() -> list[dict]:
    """Read the trimmed real-API fixture: 2 intervals x 3 regions."""
    with FIXTURE_PATH.open() as f:
        return json.load(f)["data"]


EXPECTED_COLUMNS = {
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


def test_parse_regional_rows_grain_is_region_times_interval() -> None:
    """The fundamental invariant of the regional parser: one output row per
    (interval x region). The fixture has 2 intervals x 3 regions = 6 rows.
    """
    intervals = _load_fixture()
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)

    assert len(df) == 6
    assert set(df.columns) == EXPECTED_COLUMNS


def test_parse_regional_rows_flattens_nested_structure_correctly() -> None:
    """The API nests regions inside each interval. The parser must produce
    a row per (region, interval) — verify by checking that each region_id
    appears once per interval.
    """
    intervals = _load_fixture()
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)

    counts = df.groupby("region_id").size()
    assert counts.tolist() == [2, 2, 2], "Each region should appear in both intervals"
    assert set(df["region_id"]) == {1, 10, 18}


def test_parse_regional_rows_always_returns_nan_for_actual() -> None:
    """The `/regional/intensity/{from}/{to}` endpoint does NOT provide
    `actual` intensity (model-only). The parser must surface this as NaN,
    not raise a KeyError.
    """
    intervals = _load_fixture()
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)

    assert df["intensity_actual_gco2_per_kwh"].isna().all()


def test_parse_regional_rows_preserves_region_metadata() -> None:
    """region_shortname and region_dnoregion must match the API's values
    byte-for-byte — they're the join key candidates for downstream models.
    """
    intervals = _load_fixture()
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)

    by_region = df.groupby("region_id").first()
    assert by_region.loc[1, "region_shortname"] == "North Scotland"
    assert by_region.loc[10, "region_shortname"] == "East England"
    assert by_region.loc[18, "region_shortname"] == "GB"


def test_parse_regional_rows_handles_missing_intensity_keys_gracefully() -> None:
    """Constructed edge case: a region row arrives without an `intensity`
    sub-dict. The parser must produce a row with NaN/None values rather
    than raise.
    """
    intervals = [
        {
            "from": "2026-05-31T21:30Z",
            "to": "2026-05-31T22:00Z",
            "regions": [
                {
                    "regionid": 1,
                    "dnoregion": "Scottish Hydro Electric Power Distribution",
                    "shortname": "North Scotland",
                    # intensity sub-dict omitted entirely
                }
            ],
        }
    ]
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)
    assert len(df) == 1
    assert pd.isna(df["intensity_forecast_gco2_per_kwh"].iloc[0])
    assert df["index_band"].iloc[0] is None


def test_parse_regional_rows_handles_empty_data_list() -> None:
    """Empty list in → empty DataFrame out, no exceptions."""
    df = _parse_regional_rows([], fetched_at_utc=FIXED_FETCHED_AT)
    assert len(df) == 0


def test_parse_regional_rows_broadcasts_fetched_at_across_all_rows() -> None:
    """All rows in the batch share one ingestion timestamp."""
    intervals = _load_fixture()
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)
    assert (df["_fetched_at_utc"] == FIXED_FETCHED_AT).all()


def test_parse_regional_rows_preserves_fractional_intensity_values() -> None:
    """The API occasionally returns decimal intensity values. The parser
    must NOT round or truncate them — staging is responsible for any type
    coercion (per Phase 3's numeric(6,1) cast policy).
    """
    intervals = [
        {
            "from": "2026-05-31T21:30Z",
            "to": "2026-05-31T22:00Z",
            "regions": [
                {
                    "regionid": 1,
                    "dnoregion": "Scottish Hydro Electric Power Distribution",
                    "shortname": "North Scotland",
                    "intensity": {"forecast": 123.7, "index": "moderate"},
                }
            ],
        }
    ]
    df = _parse_regional_rows(intervals, fetched_at_utc=FIXED_FETCHED_AT)
    assert df["intensity_forecast_gco2_per_kwh"].iloc[0] == pytest.approx(123.7)
