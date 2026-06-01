"""Unit tests for the pure parsing helper in carbon_intensity.py.

These tests pin the contract of `_parse_intensity_rows` without any network
or wall-clock dependencies. Phase 4's regional asset will follow the same
fixture-driven TDD pattern.
"""

from datetime import UTC, datetime

import pandas as pd
import pytest

from uk_grid.assets.carbon_intensity import _parse_intensity_rows

# Fixed wall-clock timestamp so test output is deterministic across runs.
FIXED_FETCHED_AT = datetime(2026, 5, 31, 22, 0, tzinfo=UTC)


def _sample_api_row(
    from_iso: str = "2026-05-31T21:30Z",
    to_iso: str = "2026-05-31T22:00Z",
    *,
    forecast: int | float | None = 150,
    actual: int | float | None = 140,
    index: str | None = "moderate",
) -> dict:
    """Shape-of-API helper. Real API rows look like this."""
    return {
        "from": from_iso,
        "to": to_iso,
        "intensity": {
            "forecast": forecast,
            "actual": actual,
            "index": index,
        },
    }


EXPECTED_COLUMNS = {
    "interval_start_utc",
    "interval_end_utc",
    "intensity_forecast_gco2_per_kwh",
    "intensity_actual_gco2_per_kwh",
    "index_band",
    "_fetched_at_utc",
}


def test_parse_intensity_rows_happy_path_schema() -> None:
    """Two well-formed rows in → two rows out with the full column set."""
    rows = [
        _sample_api_row(),
        _sample_api_row(
            from_iso="2026-05-31T22:00Z",
            to_iso="2026-05-31T22:30Z",
            forecast=140,
            actual=130,
            index="low",
        ),
    ]
    df = _parse_intensity_rows(rows, fetched_at_utc=FIXED_FETCHED_AT)

    assert len(df) == 2
    assert set(df.columns) == EXPECTED_COLUMNS
    assert df["intensity_actual_gco2_per_kwh"].tolist() == [140, 130]
    assert df["index_band"].tolist() == ["moderate", "low"]


def test_parse_intensity_rows_null_actual_preserved_as_nan() -> None:
    """Day-ahead intervals have ``actual: None`` — must become NaN, not raise."""
    rows = [_sample_api_row(actual=None)]
    df = _parse_intensity_rows(rows, fetched_at_utc=FIXED_FETCHED_AT)

    assert len(df) == 1
    assert pd.isna(df["intensity_actual_gco2_per_kwh"].iloc[0])
    # forecast should still be present alongside the missing actual
    assert df["intensity_forecast_gco2_per_kwh"].iloc[0] == 150


def test_parse_intensity_rows_missing_intensity_subdict_does_not_raise() -> None:
    """If the API ever returns a row without an ``intensity`` sub-dict, the
    parser should still produce a row with NaN/None values rather than crash.
    """
    rows = [{"from": "2026-05-31T21:30Z", "to": "2026-05-31T22:00Z"}]
    df = _parse_intensity_rows(rows, fetched_at_utc=FIXED_FETCHED_AT)

    assert len(df) == 1
    assert pd.isna(df["intensity_forecast_gco2_per_kwh"].iloc[0])
    assert pd.isna(df["intensity_actual_gco2_per_kwh"].iloc[0])
    assert df["index_band"].iloc[0] is None


def test_parse_intensity_rows_empty_input_yields_empty_frame() -> None:
    """Empty rows list → empty DataFrame (zero rows). Columns may be absent
    when the DataFrame is constructed from an empty list — that's fine and
    matches pandas' standard behaviour.
    """
    df = _parse_intensity_rows([], fetched_at_utc=FIXED_FETCHED_AT)
    assert len(df) == 0


def test_parse_intensity_rows_broadcasts_fetched_at_utc_across_all_rows() -> None:
    """Every row in the batch shares the same ingestion timestamp."""
    rows = [_sample_api_row(), _sample_api_row(), _sample_api_row()]
    df = _parse_intensity_rows(rows, fetched_at_utc=FIXED_FETCHED_AT)

    assert (df["_fetched_at_utc"] == FIXED_FETCHED_AT).all()


def test_parse_intensity_rows_preserves_fractional_intensity_values() -> None:
    """The API occasionally returns decimal intensity values. The parser must
    NOT round or truncate them — the staging model is responsible for any
    type coercion. Catches regressions where someone introduces an int() call.
    """
    rows = [_sample_api_row(forecast=145.7, actual=132.3)]
    df = _parse_intensity_rows(rows, fetched_at_utc=FIXED_FETCHED_AT)

    assert df["intensity_forecast_gco2_per_kwh"].iloc[0] == pytest.approx(145.7)
    assert df["intensity_actual_gco2_per_kwh"].iloc[0] == pytest.approx(132.3)
