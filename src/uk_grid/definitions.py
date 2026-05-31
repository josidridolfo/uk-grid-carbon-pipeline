"""Dagster Definitions object — the entrypoint Dagster looks for.

Configured via pyproject.toml's [tool.dagster] section; `dagster dev` finds this
module automatically.
"""

from __future__ import annotations

import dagster as dg

from uk_grid.assets import carbon_intensity, grid_eso, met_office, neso_geo
from uk_grid.resources import get_snowflake_io_manager

all_assets = dg.load_assets_from_modules([carbon_intensity, grid_eso, met_office, neso_geo])

defs = dg.Definitions(
    assets=all_assets,
    resources={
        "io_manager": get_snowflake_io_manager(),
    },
)
