---
title: "Why the Carbon Intensity API and the NESO DNO GeoJSON don't quite agree — and what a 14-row seed table fixes"
slug: why-dno-region-reconciliation-matters
published_at: 2026-05-30
description: "Three regions disagree on names. Numeric IDs are completely different. Company names are pre-2021. Here's why this matters and how an explicit reconciliation seed prevents brittle string joins from rotting your analytics."
tags: [methodology, dbt, data-quality]
---

When you build a regional carbon intensity map of the UK, the first thing you reach for is the [NESO open data portal](https://www.neso.energy/data-portal) for the DNO licence area GeoJSON polygons, and the [Carbon Intensity API](https://carbonintensity.org.uk/) for the actual intensity values. Both are authoritative, both are published by organisations that know the UK grid well. They do not agree on names, IDs, or company names. Here is a precise account of every mismatch and why it matters.

---

## The setup: two ID schemes that share nothing

The Carbon Intensity API identifies regions with a numeric `regionid` field, running from **1 to 14**. Region 1 is North Scotland. Region 14 is South England. These IDs are stable and have not changed since the API launched.

The NESO GeoJSON file identifies the same 14 geographic areas with a `properties.ID` field, but the values run from **10 to 23**. There is no mathematical relationship between the two schemes — it is not an offset, it is not a lookup table you can derive algorithmically. The GeoJSON `ID=10` does not correspond to API `regionid=10`. They are simply different numbering systems applied independently to the same geography.

A naive `JOIN ON api.regionid = geojson.id` will produce results — it will join some rows — but those rows will be wrong. The join will silently associate South Scotland intensity values with North Wales polygons and vice versa. This class of bug produces plausible-looking maps that show the wrong colours in the wrong places, with no error raised anywhere in the pipeline.

The reconciliation seed at [`dbt/seeds/dno_region_mapping.csv`](https://github.com/josidridolfo/uk-grid-carbon-pipeline/blob/main/dbt/seeds/dno_region_mapping.csv) has columns:

```
api_regionid, api_shortname, geojson_id, geojson_name, dno_company_name, canonical_name
```

Every row maps one `api_regionid` to its corresponding `geojson_id`. It was built by reading both datasets side by side and matching geographies by visual inspection of the polygons and cross-referencing the Carbon Intensity API documentation. It is 14 rows. It is the entire solution.

---

## Three specific name mismatches

Beyond the ID problem, three regions have names that differ between the two sources in ways that make string-matching fragile:

**1. South Scotland**

- Carbon Intensity API `shortname`: `South Scotland`
- NESO GeoJSON `properties.name`: `South and Central Scotland`

The GeoJSON name is more geographically precise — the licence area genuinely covers both the south and the central belt. The API name is shorter. Neither is wrong. A `LOWER(TRIM(...))` normalisation will not save you here because the words themselves differ.

**2. North Wales & Merseyside**

- Carbon Intensity API `shortname`: `North Wales & Merseyside`
- NESO GeoJSON `properties.name`: `North Wales, Merseyside and Cheshire`

The GeoJSON includes Cheshire explicitly; the API does not. This matters if you are cross-referencing with Ofgem licence boundary data, which uses yet a third naming convention.

**3. South England**

- Carbon Intensity API `shortname`: `South England`
- NESO GeoJSON `properties.name`: `Southern England`

One word difference. A fuzzy string match with a high threshold would probably catch this one, but "probably" is not a test that passes at `dbt build` time.

If you wrote `JOIN ON LOWER(api.shortname) = LOWER(geojson.name)`, none of these three joins would match. You would silently drop three of 14 regions from every query, and your regional map would have three holes — visible only if you checked row counts, not if you just looked at the rendered chart.

---

## The 2021 DNO rebrand

The Carbon Intensity API's `shortname` values encode a further historical artefact: the company names they reference are pre-2021 corporate names. In 2021, three major UK DNOs rebranded:

| Legacy name (in API) | Post-2021 name |
|---|---|
| Western Power Distribution (WPD) | National Grid Electricity Distribution (NGED) |
| SP Distribution | SP Energy Networks |
| Scottish Hydro Electric Power Distribution | SSEN Transmission / SSEN Distribution |

The API still returns the legacy shortnames in its response payload. The NESO GeoJSON uses a mix of legacy and current names depending on when the file was last updated. Neither source is consistently up to date with the current Ofgem licence holder names.

The reconciliation seed stores a `dno_company_name` (current, post-2021) and a `canonical_name` (the short label shown in UI elements) separately from the API and GeoJSON names. Downstream queries join on `api_regionid` — a numeric key that is stable regardless of corporate rebranding — and surface `canonical_name` for display.

---

## The seed: why 14 rows of CSV beats everything else

`dbt/seeds/dno_region_mapping.csv` is loaded by `dbt seed` into `RAW.DNO_REGION_MAPPING`. It is plain CSV, committed to git alongside the dbt models, and visible in pull request diffs. Adding a column, correcting a name, or handling a future rebrand is a one-line CSV edit followed by `dbt seed --select dno_region_mapping && dbt build --select dim_dno_region+`.

The alternatives considered and rejected:

- **Hardcoded Python dict in the ingestion code** — hidden inside application code, not visible to the data team, not tested by dbt, breaks separation of concerns between ingestion and transformation.
- **A database lookup table managed via Django admin** — unnecessary operational complexity for a 14-row static mapping; introduces a write path where none is needed.
- **Fuzzy string matching at query time** — non-deterministic, expensive on large result sets, and fails on the South Scotland / South and Central Scotland pair where no reasonable threshold simultaneously accepts the correct match and rejects similar-but-wrong matches.

---

## The downstream payoff

Because `dim_dno_region` joins the reconciliation seed to the GeoJSON polygons in a single dbt model, every downstream mart can reference `dno_region_id` as a stable surrogate key and get correct names, correct polygons, and correct API linkage from a single join:

```sql
-- fact_regional_carbon_intensity → dim_dno_region → GEOGRAPHY polygon
SELECT
    f.settlement_date,
    f.settlement_period,
    d.canonical_name,
    d.region_geog,       -- GEOGRAPHY column for spatial joins
    f.carbon_intensity_actual
FROM analytics_marts.fact_regional_carbon_intensity f
JOIN analytics_marts.dim_dno_region d
    ON f.dno_region_id = d.dno_region_id
WHERE f.settlement_date = CURRENT_DATE
ORDER BY d.canonical_name, f.settlement_period;
```

The `region_geog` column enables point-in-polygon queries — for example, "given a postcode centroid, which DNO region is it in?" — without any GIS preprocessing outside Snowflake. That query pattern is the foundation of the regional smart-charging analysis: derive the DNO region from a user's postcode, then retrieve the optimal charging window for that region's carbon intensity profile.

The 88 dbt tests include a `relationships` constraint between `fact_regional_carbon_intensity.dno_region_id` and `dim_dno_region.dno_region_id`. If the seed is ever corrupted — a duplicate row, a changed `api_regionid` — the build fails with a clear error before any bad data reaches the marts. That constraint is the automated equivalent of the visual inspection that built the seed in the first place.
