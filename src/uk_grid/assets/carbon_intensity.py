"""Carbon Intensity API ingestion.

The Carbon Intensity API is run by National Grid ESO and EDF Europe. It exposes
half-hourly carbon intensity values (gCO2/kWh) for GB as a whole and for each of
the 14 DNO regions.

Endpoint: https://api.carbonintensity.org.uk
No authentication required. Rate limit is generous (we stay well under it).

This is the FIRST working asset in the project — the rest of the pipeline (other
sources, dbt models, dashboard) follows the same pattern.
"""

from datetime import UTC, datetime, timedelta

import dagster as dg
import httpx
import pandas as pd
from dagster import AssetExecutionContext
from tenacity import retry, stop_after_attempt, wait_exponential

API_BASE = "https://api.carbonintensity.org.uk"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(url: str) -> dict:
    """GET wrapper with retry/backoff."""
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    return response.json()


def _parse_intensity_rows(
    rows: list[dict],
    *,
    fetched_at_utc: datetime,
) -> pd.DataFrame:
    """Parse Carbon Intensity API response rows into a typed DataFrame.

    Pure function — deterministic given identical input. Network I/O and
    wall-clock reads live in the ``@dg.asset``-decorated wrapper above so this
    helper can be unit-tested in isolation (see tests/test_carbon_intensity_parse.py).

    Args:
        rows: List of dicts from the API's ``"data"`` key. Each row has
            ``"from"``/``"to"`` ISO timestamps and an ``"intensity"`` sub-dict
            with ``"forecast"``/``"actual"``/``"index"`` keys — any of which
            may be missing or ``None`` (e.g. ``actual`` is ``None`` for
            day-ahead intervals that have not yet settled).
        fetched_at_utc: Wall-clock ingestion timestamp, broadcast across all
            rows so the whole batch shares one ``_fetched_at_utc`` value.

    Returns:
        DataFrame with one row per input row and columns: ``interval_start_utc``,
        ``interval_end_utc``, ``intensity_forecast_gco2_per_kwh``,
        ``intensity_actual_gco2_per_kwh``, ``index_band``, ``_fetched_at_utc``.
        Empty list in → empty DataFrame out.
    """
    return pd.DataFrame(
        [
            {
                "interval_start_utc": pd.to_datetime(r["from"], utc=True),
                "interval_end_utc": pd.to_datetime(r["to"], utc=True),
                "intensity_forecast_gco2_per_kwh": r.get("intensity", {}).get("forecast"),
                "intensity_actual_gco2_per_kwh": r.get("intensity", {}).get("actual"),
                "index_band": r.get("intensity", {}).get("index"),
                "_fetched_at_utc": fetched_at_utc,
            }
            for r in rows
        ]
    )


def _parse_regional_rows(
    intervals: list[dict],
    *,
    fetched_at_utc: datetime,
) -> pd.DataFrame:
    """Parse Carbon Intensity API's ``/regional/intensity/{from}/{to}`` response.

    Pure function — deterministic given identical input. The API nests regions
    inside each interval; this parser flattens to one row per (interval x region).

    Grain: ``(interval_start_utc, region_id)`` — 18 regions x N intervals.

    Args:
        intervals: List of interval dicts from the API's ``"data"`` key. Each
            has ``"from"``/``"to"`` ISO timestamps and a ``"regions"`` list with
            one dict per region: ``{"regionid": int, "shortname": str,
            "dnoregion": str, "intensity": {"forecast": float, "index": str},
            "generationmix": [...]}``. The ``"intensity"`` sub-dict may omit
            keys or be missing entirely for malformed rows. The regional
            endpoint does NOT return ``"actual"`` (model-only intensity) —
            the parser still emits an ``intensity_actual_gco2_per_kwh``
            column for schema parity with the national parser, always NaN.
        fetched_at_utc: Wall-clock ingestion timestamp, broadcast across all
            output rows so the entire batch shares one ``_fetched_at_utc``.

    Returns:
        DataFrame with columns: ``interval_start_utc``, ``interval_end_utc``,
        ``region_id``, ``region_shortname``, ``region_dnoregion``,
        ``intensity_forecast_gco2_per_kwh``, ``intensity_actual_gco2_per_kwh``,
        ``index_band``, ``_fetched_at_utc``. The ``generationmix`` field is
        intentionally NOT extracted here — it's a nested list that will be
        modelled as its own asset/mart in a future phase.
    """
    rows: list[dict] = []
    for interval in intervals:
        interval_start = pd.to_datetime(interval["from"], utc=True)
        interval_end = pd.to_datetime(interval["to"], utc=True)
        for region in interval.get("regions", []):
            intensity = region.get("intensity", {}) or {}
            rows.append(
                {
                    "interval_start_utc": interval_start,
                    "interval_end_utc": interval_end,
                    "region_id": region.get("regionid"),
                    "region_shortname": region.get("shortname"),
                    "region_dnoregion": region.get("dnoregion"),
                    "intensity_forecast_gco2_per_kwh": intensity.get("forecast"),
                    "intensity_actual_gco2_per_kwh": intensity.get("actual"),
                    "index_band": intensity.get("index"),
                    "_fetched_at_utc": fetched_at_utc,
                }
            )
    return pd.DataFrame(rows)


@dg.asset(
    description=(
        "Half-hourly UK national carbon intensity actuals (gCO2/kWh) for the trailing "
        "24 hours. Re-run hourly to keep the staging view fresh."
    ),
    group_name="carbon_intensity",
    metadata={"source": "https://api.carbonintensity.org.uk/intensity"},
    compute_kind="python",
)
def raw_carbon_intensity__national(context: AssetExecutionContext) -> pd.DataFrame:
    """Pull the last 24 hours of national half-hour intensity from the Carbon Intensity API."""
    end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=24)
    url = (
        f"{API_BASE}/intensity/"
        f"{start.strftime('%Y-%m-%dT%H:%MZ')}/"
        f"{end.strftime('%Y-%m-%dT%H:%MZ')}"
    )
    payload = _get(url)
    rows = payload["data"]

    df = _parse_intensity_rows(rows, fetched_at_utc=datetime.now(UTC))

    context.log.info(
        f"Fetched {len(df)} half-hourly intervals "
        f"from {start.isoformat()} to {end.isoformat()}"
    )
    context.add_output_metadata(
        {
            "row_count": len(df),
            "min_interval_start": str(df["interval_start_utc"].min()) if len(df) else None,
            "max_interval_start": str(df["interval_start_utc"].max()) if len(df) else None,
            "mean_intensity_actual": (
                float(df["intensity_actual_gco2_per_kwh"].mean()) if len(df) else None
            ),
        }
    )
    return df


@dg.asset(
    description=(
        "Half-hourly UK carbon intensity for the trailing 24h, broken out by the 18 "
        "regions the Carbon Intensity API exposes (14 DNO licence areas + 3 nation "
        "aggregates + GB total). Grain: (interval, region). The regional endpoint "
        "provides forecast-only intensity (model-derived); `actual` is always NaN here, "
        "in contrast to the national endpoint."
    ),
    group_name="carbon_intensity",
    metadata={"source": "https://api.carbonintensity.org.uk/regional/intensity"},
    compute_kind="python",
)
def raw_carbon_intensity__regional(context: AssetExecutionContext) -> pd.DataFrame:
    """Pull the last 24 hours of regional half-hour intensity from the Carbon Intensity API."""
    end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(hours=24)
    url = (
        f"{API_BASE}/regional/intensity/"
        f"{start.strftime('%Y-%m-%dT%H:%MZ')}/"
        f"{end.strftime('%Y-%m-%dT%H:%MZ')}"
    )
    payload = _get(url)
    intervals = payload["data"]

    df = _parse_regional_rows(intervals, fetched_at_utc=datetime.now(UTC))

    context.log.info(
        f"Fetched {len(df)} (interval x region) rows "
        f"from {start.isoformat()} to {end.isoformat()}"
    )
    context.add_output_metadata(
        {
            "row_count": len(df),
            "interval_count": len(intervals),
            "region_count": (df["region_id"].nunique() if len(df) else 0),
            "min_interval_start": str(df["interval_start_utc"].min()) if len(df) else None,
            "max_interval_start": str(df["interval_start_utc"].max()) if len(df) else None,
            "mean_intensity_forecast": (
                float(df["intensity_forecast_gco2_per_kwh"].mean()) if len(df) else None
            ),
        }
    )
    return df
