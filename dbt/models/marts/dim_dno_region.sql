{{ config(materialized='table') }}

with polygons as (
    select * from {{ ref('stg_neso__dno_polygons') }}
),

mapping as (
    select * from {{ ref('dno_region_mapping') }}
)

select
    m.api_regionid,
    m.api_shortname,
    m.api_dnoregion_legacy,
    p.geojson_id,
    p.area_name as geojson_area,
    m.dno_code,
    m.dno_full_current,
    m.nation,
    p.polygon,
    st_centroid(p.polygon) as polygon_centroid
from mapping m
inner join polygons p on m.geojson_id = p.geojson_id
