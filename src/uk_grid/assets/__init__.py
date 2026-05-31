"""Dagster asset definitions, grouped by source domain.

One module per source so it's easy to read the surface area at a glance.
"""

from uk_grid.assets import carbon_intensity, grid_eso, met_office, neso_geo  # noqa: F401
