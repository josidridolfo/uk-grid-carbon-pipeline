"""National Grid ESO open data ingestion — STUB.

Sources to wire up:
- Historic Generation Mix: https://www.nationalgrideso.com/data-portal/historic-generation-mix
- Electricity demand: https://www.nationalgrideso.com/data-portal/half-hourly-electricity-demand-data
- Settlement prices and BMRS feeds.

Pattern: copy carbon_intensity.py and adapt to the ESO endpoints.
"""

import dagster as dg
import pandas as pd
from dagster import AssetExecutionContext


@dg.asset(
    description="STUB: Half-hourly GB generation mix by fuel type from National Grid ESO.",
    group_name="grid_eso",
    compute_kind="python",
)
def raw_grid_eso__generation_by_fuel(context: AssetExecutionContext) -> pd.DataFrame:
    """TODO: implement. Pull the historic generation mix CSV from ESO's data portal."""
    context.log.warning("raw_grid_eso__generation_by_fuel is a stub — returning empty frame.")
    return pd.DataFrame()


@dg.asset(
    description="STUB: Half-hourly GB national demand from National Grid ESO.",
    group_name="grid_eso",
    compute_kind="python",
)
def raw_grid_eso__demand(context: AssetExecutionContext) -> pd.DataFrame:
    """TODO: implement."""
    context.log.warning("raw_grid_eso__demand is a stub — returning empty frame.")
    return pd.DataFrame()
