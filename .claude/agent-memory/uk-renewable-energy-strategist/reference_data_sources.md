---
name: reference-data-sources
description: Authoritative UK/EU public data sources used or recommended for this project, with access details
metadata:
  type: reference
---

## Active in this project

| Source | URL | Auth | Licence | Notes |
|--------|-----|------|---------|-------|
| Carbon Intensity API | https://api.carbonintensity.org.uk | None | Open | Half-hourly national + 14 DNO regions, gCO2/kWh, forecast + actual. /intensity for national, /regional for regions. |
| Met Office DataPoint | https://www.metoffice.gov.uk/services/data/datapoint | Free API key | OGL | Hourly obs + 3-hourly forecasts for ~5000 UK sites. Set MET_OFFICE_API_KEY in .env |
| NESO Historic Generation Mix | https://www.nationalgrideso.com/data-portal/historic-generation-mix | None | OGL | Half-hourly GB generation by fuel type (wind, solar, nuclear, gas, etc.). CSV download. |
| NESO Half-Hourly Demand | https://www.nationalgrideso.com/data-portal/half-hourly-electricity-demand-data | None | OGL | Half-hourly GB demand. |

## Recommended additions

| Source | URL | Auth | Licence | Notes |
|--------|-----|------|---------|-------|
| Elexon BMRS Insights API | https://developer.elexon.co.uk/bmrs-api-guidance | Free registration | Elexon ToS | Settlement period (half-hourly) demand, generation, imbalance, B1620 (actual generation per unit). Real-time + historic. |
| Octopus Energy Agile tariff API | https://api.octopus.energy/v1/products/AGILE-FLEX-22-11-25/ | None for public prices | CC-BY | Half-hourly Agile unit prices by GSP region. Free, no auth for product/tariff listing. |
| DfT EV Charging Device Stats | https://www.gov.uk/government/statistics/electric-vehicle-charging-device-statistics | None | OGL | Quarterly stats on public charge point count by LA and region. |
| National Chargepoint Registry (NCR) | https://www.gov.uk/guidance/find-and-use-data-from-the-national-chargepoint-registry | None | OGL | Live register of public charge points. |
| NESO Carbon Intensity API (regional) | https://api.carbonintensity.org.uk/regional | None | Open | 14 DNO regions. /regional/intensity/{from}/{to} gives per-region fuel mix breakdown too. |
| Open Power System Data | https://open-power-system-data.org | None | CC-BY | European generation data, useful for comparative context. |
| ENTSO-E Transparency Platform | https://transparency.entsoe.eu | Free registration | ENTSO-E ToS | EU-wide generation, demand, cross-border flows. |
| BEIS/DESNZ Sub-national Consumption | https://www.gov.uk/government/collections/sub-national-electricity-and-gas-consumption-data | None | OGL | Annual sub-national electricity/gas consumption by LSOA, MSOA, LA. |

## Data quality pitfalls to remember

- Carbon Intensity API: GMT/BST handling — all timestamps are UTC but the API uses 'from'/'to' ISO strings that include timezone offsets. Always cast to UTC explicitly (already done in stg model).
- NESO generation mix CSV: the column names change occasionally between data portal updates. Pin the column mapping in a seed or staging model with explicit renaming.
- Elexon BMRS: settlement period 1-50 (occasionally 51-52 in BST transitions). Period 1 = 00:00-00:30 in the settlement day. Do not assume period = half-hour offset directly — use the settlement date + period together.
- Met Office DataPoint: not all sites have all observation types. Filter to sites with wind speed and irradiance where possible; otherwise impute from ERA5 (Copernicus CDS).
