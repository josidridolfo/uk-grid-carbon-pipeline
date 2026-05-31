-- ============================================================================
-- snowflake_init.sql
-- ============================================================================
-- Idempotent bootstrap for the UK Grid Carbon Pipeline Snowflake account.
--
-- Creates: warehouse, database, schemas, the LOADER / TRANSFORMER / REPORTER
-- role hierarchy, and the grants each role needs. Re-running is safe — all
-- DDL is gated on IF NOT EXISTS, and Snowflake grants are no-ops when the
-- privilege is already in place.
--
-- HOW TO RUN
--   Snowsight UI: paste this file into a worksheet and Run All. ~10 seconds.
--   snowsql CLI:  snowsql -a <account> -u <user> -f infra/snowflake_init.sql
--
-- REQUIRED ROLE
--   ACCOUNTADMIN. The script will USE ROLE explicitly so role-switching is
--   transparent; you just need to be logged in as a user who can assume it.
--
-- ARCHITECTURE
--   Role hierarchy: LOADER ⊂ TRANSFORMER ⊂ SYSADMIN; REPORTER ⊂ SYSADMIN.
--   The current developer user (you, running this) is granted all three so
--   you can exercise the pipeline end-to-end locally. In a production
--   deployment you would create dedicated service users instead.
--
--   The schema layout matches the project's .env defaults:
--     UK_GRID.RAW                — Dagster raw ingestion landing zone
--     UK_GRID.ANALYTICS_STAGING  — dbt staging models (views)
--     UK_GRID.ANALYTICS_MARTS    — dbt mart models (tables)
--     UK_GRID.ANALYTICS_SEEDS    — dbt seeds (e.g., dno_region_mapping)
--
--   If you change SNOWFLAKE_DBT_SCHEMA in .env to something other than
--   ANALYTICS, dbt will auto-create the new <schema>_STAGING / <schema>_MARTS
--   schemas on first run thanks to the CREATE SCHEMA grant on the database.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. Warehouse
-- ----------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;

CREATE WAREHOUSE IF NOT EXISTS ENERGY_WH
    WAREHOUSE_SIZE      = XSMALL
    AUTO_SUSPEND        = 60
    AUTO_RESUME         = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT             = 'Compute for UK Grid Carbon Pipeline — Dagster ingestion + dbt builds + ad-hoc queries.';


-- ----------------------------------------------------------------------------
-- 2. Database + schemas
-- ----------------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS UK_GRID
    COMMENT = 'UK electricity grid carbon intensity, generation mix, and weather data.';

USE DATABASE UK_GRID;

CREATE SCHEMA IF NOT EXISTS RAW
    COMMENT = 'Raw landing zone for Dagster-ingested data. Table names prefixed by source (raw_carbon_intensity__*, raw_neso__*).';

CREATE SCHEMA IF NOT EXISTS ANALYTICS_STAGING
    COMMENT = 'dbt staging models — 1:1 with sources, view materialisation, type casts + cleaning only.';

CREATE SCHEMA IF NOT EXISTS ANALYTICS_MARTS
    COMMENT = 'dbt mart models — queryable end product, table materialisation.';

CREATE SCHEMA IF NOT EXISTS ANALYTICS_SEEDS
    COMMENT = 'dbt seeds — static reference data (e.g., DNO region cross-walk).';


-- ----------------------------------------------------------------------------
-- 3. Roles + role hierarchy
-- ----------------------------------------------------------------------------
USE ROLE SECURITYADMIN;

CREATE ROLE IF NOT EXISTS LOADER
    COMMENT = 'Writes to UK_GRID.RAW. Used by Dagster ingestion assets.';

CREATE ROLE IF NOT EXISTS TRANSFORMER
    COMMENT = 'Builds dbt models in UK_GRID.ANALYTICS_*. Reads RAW. Inherits LOADER.';

CREATE ROLE IF NOT EXISTS REPORTER
    COMMENT = 'Read-only access to UK_GRID.ANALYTICS_MARTS. Used by Streamlit and BI consumers.';

-- TRANSFORMER inherits LOADER's writes-to-RAW capability so a single role can
-- drive an end-to-end pipeline run when needed (e.g., local development).
GRANT ROLE LOADER      TO ROLE TRANSFORMER;

-- SYSADMIN sits above the working roles for ops visibility.
GRANT ROLE TRANSFORMER TO ROLE SYSADMIN;
GRANT ROLE REPORTER    TO ROLE SYSADMIN;


-- ----------------------------------------------------------------------------
-- 4. Warehouse grants
-- ----------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;

GRANT USAGE ON WAREHOUSE ENERGY_WH TO ROLE LOADER;
GRANT USAGE ON WAREHOUSE ENERGY_WH TO ROLE TRANSFORMER;
GRANT USAGE ON WAREHOUSE ENERGY_WH TO ROLE REPORTER;


-- ----------------------------------------------------------------------------
-- 5. Database-level grants
-- ----------------------------------------------------------------------------
GRANT USAGE ON DATABASE UK_GRID TO ROLE LOADER;
GRANT USAGE ON DATABASE UK_GRID TO ROLE TRANSFORMER;
GRANT USAGE ON DATABASE UK_GRID TO ROLE REPORTER;

-- dbt creates per-layer schemas dynamically (ANALYTICS_STAGING, ANALYTICS_MARTS, etc.)
-- on first run based on dbt_project.yml's +schema configs.
GRANT CREATE SCHEMA ON DATABASE UK_GRID TO ROLE TRANSFORMER;


-- ----------------------------------------------------------------------------
-- 6. Schema grants — LOADER (full control of RAW)
-- ----------------------------------------------------------------------------
GRANT USAGE, CREATE TABLE, CREATE VIEW ON SCHEMA UK_GRID.RAW TO ROLE LOADER;

GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA UK_GRID.RAW TO ROLE LOADER;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON FUTURE TABLES IN SCHEMA UK_GRID.RAW TO ROLE LOADER;


-- ----------------------------------------------------------------------------
-- 7. Schema grants — TRANSFORMER (read RAW, full control of ANALYTICS_*)
-- ----------------------------------------------------------------------------

-- Read access to RAW
GRANT USAGE ON SCHEMA UK_GRID.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON ALL    TABLES IN SCHEMA UK_GRID.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA UK_GRID.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA UK_GRID.RAW TO ROLE TRANSFORMER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA UK_GRID.RAW TO ROLE TRANSFORMER;

-- Full control of ANALYTICS_* schemas (dbt needs to create, replace, drop)
GRANT ALL PRIVILEGES ON SCHEMA UK_GRID.ANALYTICS_STAGING TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON SCHEMA UK_GRID.ANALYTICS_MARTS   TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON SCHEMA UK_GRID.ANALYTICS_SEEDS   TO ROLE TRANSFORMER;

GRANT ALL PRIVILEGES ON ALL    TABLES IN SCHEMA UK_GRID.ANALYTICS_STAGING TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON ALL    TABLES IN SCHEMA UK_GRID.ANALYTICS_MARTS   TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON ALL    TABLES IN SCHEMA UK_GRID.ANALYTICS_SEEDS   TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA UK_GRID.ANALYTICS_STAGING TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA UK_GRID.ANALYTICS_MARTS   TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON FUTURE TABLES IN SCHEMA UK_GRID.ANALYTICS_SEEDS   TO ROLE TRANSFORMER;

GRANT ALL PRIVILEGES ON ALL    VIEWS IN SCHEMA UK_GRID.ANALYTICS_STAGING TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON ALL    VIEWS IN SCHEMA UK_GRID.ANALYTICS_MARTS   TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON FUTURE VIEWS IN SCHEMA UK_GRID.ANALYTICS_STAGING TO ROLE TRANSFORMER;
GRANT ALL PRIVILEGES ON FUTURE VIEWS IN SCHEMA UK_GRID.ANALYTICS_MARTS   TO ROLE TRANSFORMER;


-- ----------------------------------------------------------------------------
-- 8. Schema grants — REPORTER (read-only on ANALYTICS_MARTS)
-- ----------------------------------------------------------------------------
GRANT USAGE ON SCHEMA UK_GRID.ANALYTICS_MARTS TO ROLE REPORTER;
GRANT SELECT ON ALL    TABLES IN SCHEMA UK_GRID.ANALYTICS_MARTS TO ROLE REPORTER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA UK_GRID.ANALYTICS_MARTS TO ROLE REPORTER;
GRANT SELECT ON ALL    VIEWS  IN SCHEMA UK_GRID.ANALYTICS_MARTS TO ROLE REPORTER;
GRANT SELECT ON FUTURE VIEWS  IN SCHEMA UK_GRID.ANALYTICS_MARTS TO ROLE REPORTER;


-- ----------------------------------------------------------------------------
-- 9. Grant roles to the running user
--
-- Detects the user executing this script and grants all three working roles.
-- For a service-account deployment, replace the SET statement with:
--   SET my_user = '<SERVICE_ACCOUNT_USERNAME>';
-- ----------------------------------------------------------------------------
USE ROLE SECURITYADMIN;

SET my_user = (SELECT CURRENT_USER());

GRANT ROLE LOADER      TO USER IDENTIFIER($my_user);
GRANT ROLE TRANSFORMER TO USER IDENTIFIER($my_user);
GRANT ROLE REPORTER    TO USER IDENTIFIER($my_user);


-- ----------------------------------------------------------------------------
-- 10. Sanity check
-- ----------------------------------------------------------------------------
USE ROLE TRANSFORMER;
USE WAREHOUSE ENERGY_WH;
USE DATABASE UK_GRID;

SELECT 'Bootstrap complete — TRANSFORMER role can use ENERGY_WH on UK_GRID.' AS status;
SHOW SCHEMAS IN DATABASE UK_GRID;
