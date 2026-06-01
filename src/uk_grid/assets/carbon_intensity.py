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
        "Per-region half-hourly carbon intensity for the 14 GB DNO regions. "
        "TODO: implement; see https://api.carbonintensity.org.uk/regional"
    ),
    group_name="carbon_intensity",
    compute_kind="python",
)
def raw_carbon_intensity__regional(context: AssetExecutionContext) -> pd.DataFrame:
    """Pull regional intensity. TODO: implement once national loop is verified end-to-end."""
    context.log.warning("raw_carbon_intensity__regional is a stub — returning empty frame.")
    return pd.DataFrame()
