"""Met Office DataPoint ingestion — STUB.

Met Office DataPoint provides observations and forecasts for sites across the UK.
Requires a free API key (set MET_OFFICE_API_KEY in .env).

API base: http://datapoint.metoffice.gov.uk/public/data/

Pattern: copy carbon_intensity.py and adapt.
"""

import dagster as dg
import pandas as pd
from dagster import AssetExecutionContext


@dg.asset(
    description="STUB: Hourly weather observations across selected GB sites.",
    group_name="met_office",
    compute_kind="python",
)
def raw_met_office__observations(context: AssetExecutionContext) -> pd.DataFrame:
    """TODO: implement once carbon intensity loop is verified end-to-end."""
    context.log.warning("raw_met_office__observations is a stub — returning empty frame.")
    return pd.DataFrame()
