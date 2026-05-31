"""NESO DNO Licence Areas geo ingestion.

Reads the GB DNO Licence Areas GeoJSON from disk, reprojects each polygon from
EPSG:27700 (British National Grid) to EPSG:4326 (WGS84) so it can be stored as
a Snowflake GEOGRAPHY, and lands a flat DataFrame in the RAW_NESO schema.

Source: National Energy SO Open Data
File: data/reference/gb_dno_licence_areas_20240503.geojson
Licence: NESO Open Data Licence (https://www.neso.energy/data-portal/ngeso-open-licence)

This asset is static reference data. It should be materialised manually when the
underlying GeoJSON is updated; it does NOT auto-materialise.
"""

import json
from pathlib import Path

import dagster as dg
import pandas as pd
from dagster import AssetExecutionContext
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

_GEOJSON_PATH = (
    Path(__file__).parent.parent.parent.parent / "data" / "reference" / "gb_dno_licence_areas_20240503.geojson"
)

# EPSG:27700 (British National Grid) → EPSG:4326 (WGS84, lon/lat)
# always_xy=True ensures output is (longitude, latitude), matching GeoJSON convention
# and Snowflake's GEOGRAPHY expectations.
_TRANSFORMER = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)


def _reproject_geometry(geom_dict: dict) -> str:
    """Reproject a GeoJSON geometry dict from EPSG:27700 to EPSG:4326.

    Returns the reprojected geometry as a WKT string suitable for passing to
    Snowflake's TO_GEOGRAPHY() function.
    """
    shapely_geom = shape(geom_dict)
    reprojected = transform(_TRANSFORMER.transform, shapely_geom)
    return reprojected.wkt


@dg.asset(
    description=(
        "GB DNO licence area polygons from the NESO data portal. "
        "Geometries reprojected from EPSG:27700 (British National Grid) to "
        "EPSG:4326 (WGS84) for Snowflake GEOGRAPHY compatibility. "
        "14 features — one per DNO licence area. "
        "Static reference data; materialise manually when the source file is updated."
    ),
    group_name="neso_geo",
    compute_kind="python",
    metadata={
        "source": "https://www.neso.energy/data-portal/gis-boundaries-gb-dno-licence-areas",
        "licence": "https://www.neso.energy/data-portal/ngeso-open-licence",
        "source_crs": "EPSG:27700",
        "output_crs": "EPSG:4326",
    },
)
def raw_neso__dno_polygons(context: AssetExecutionContext) -> pd.DataFrame:
    """Read DNO licence area GeoJSON, reproject to WGS84, return as flat DataFrame."""
    context.log.info(f"Reading GeoJSON from {_GEOJSON_PATH}")

    with _GEOJSON_PATH.open() as f:
        geojson = json.load(f)

    features = geojson["features"]
    context.log.info(f"Found {len(features)} features in GeoJSON")

    rows = []
    for feature in features:
        props = feature["properties"]
        geometry_wkt = _reproject_geometry(feature["geometry"])
        rows.append(
            {
                "geojson_id": int(props["ID"]),
                "area_name": str(props["Area"]),
                "dno_code": str(props["DNO"]),
                "dno_full": str(props["DNO_Full"]),
                "geometry_wkt": geometry_wkt,
            }
        )

    df = pd.DataFrame(rows)

    context.log.info(f"Reprojected {len(df)} polygons from EPSG:27700 to EPSG:4326")
    context.add_output_metadata(
        {
            "row_count": len(df),
            "source_crs": "EPSG:27700",
            "output_crs": "EPSG:4326",
            "geojson_ids": dg.MetadataValue.json(sorted(df["geojson_id"].tolist())),
            "dno_codes": dg.MetadataValue.json(sorted(df["dno_code"].unique().tolist())),
            "preview": dg.MetadataValue.md(
                df[["geojson_id", "area_name", "dno_code"]].to_markdown(index=False)
            ),
        }
    )
    return df
