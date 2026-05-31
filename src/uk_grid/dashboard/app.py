"""Streamlit dashboard reading directly from the DuckDB warehouse.

Run with: `make dashboard` or `streamlit run dashboard/app.py`.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

DUCKDB_PATH = Path("data/uk_grid.duckdb")


@st.cache_data(ttl=60)
def load_carbon_intensity_hourly() -> pd.DataFrame:
    """Read the hourly carbon intensity mart from DuckDB."""
    if not DUCKDB_PATH.exists():
        return pd.DataFrame()
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    df = con.execute(
        "select * from main_marts.fact_carbon_intensity_hourly order by hour_start_utc"
    ).fetchdf()
    con.close()
    return df


def main() -> None:
    st.set_page_config(page_title="UK Grid Carbon Intensity", layout="wide")
    st.title("UK Grid Carbon Intensity")
    st.caption(
        "When is the UK electricity grid greenest? Half-hourly carbon intensity, "
        "aggregated to the hour. Data from the [Carbon Intensity API]"
        "(https://carbonintensity.org.uk/)."
    )

    df = load_carbon_intensity_hourly()

    if df.empty:
        st.warning(
            "No data yet. Run the pipeline first:\n\n"
            "```bash\nmake dev      # materialise raw assets in Dagster\n"
            "make dbt-build  # build the dbt models\n```"
        )
        return

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Hours of data",
        f"{len(df):,}",
    )
    col2.metric(
        "Mean intensity (gCO2/kWh)",
        f"{df['mean_intensity_actual_gco2_per_kwh'].mean():.0f}",
    )
    col3.metric(
        "Greenest hour so far",
        f"{df['mean_intensity_actual_gco2_per_kwh'].min():.0f} gCO2/kWh",
    )

    chart = (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("hour_start_utc:T", title="Hour (UTC)"),
            y=alt.Y(
                "mean_intensity_actual_gco2_per_kwh:Q",
                title="Carbon intensity (gCO2/kWh)",
            ),
            tooltip=["hour_start_utc:T", "mean_intensity_actual_gco2_per_kwh:Q"],
        )
        .properties(height=400)
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
