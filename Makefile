# Common developer targets. Run `make help` for a list.

.PHONY: help install snowflake-init dev dagster dbt-deps dbt-build dbt-test dbt-docs dashboard lint format clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python dependencies via uv
	uv sync

snowflake-init: ## Bootstrap Snowflake (warehouse, db, schemas, roles, grants). Idempotent.
	@if ! command -v snowsql >/dev/null 2>&1; then \
		echo "Error: snowsql not installed."; \
		echo "  Install: https://docs.snowflake.com/en/user-guide/snowsql-install-config"; \
		echo "  Or:      paste infra/snowflake_init.sql into the Snowsight UI and Run All"; \
		exit 1; \
	fi
	@if [ ! -f .env ]; then \
		echo "Error: .env not found. Copy .env.example to .env and populate it first."; \
		exit 1; \
	fi
	@set -a && . ./.env && set +a && \
		SNOWSQL_PWD="$${SNOWFLAKE_PASSWORD}" snowsql \
			-a "$${SNOWFLAKE_ACCOUNT:?Set SNOWFLAKE_ACCOUNT in .env}" \
			-u "$${SNOWFLAKE_USER:?Set SNOWFLAKE_USER in .env}" \
			-f infra/snowflake_init.sql

dev: ## Start Dagster dev UI (http://localhost:3000)
	uv run dagster dev

dbt-deps: ## Install dbt packages (run after pulling changes)
	@set -a && . ./.env && set +a && uv run dbt deps --project-dir dbt --profiles-dir dbt

dbt-build: ## Run all dbt models + tests
	@set -a && . ./.env && set +a && uv run dbt build --project-dir dbt --profiles-dir dbt

dbt-test: ## Run dbt tests only
	@set -a && . ./.env && set +a && uv run dbt test --project-dir dbt --profiles-dir dbt

dbt-docs: ## Generate and serve dbt docs at http://localhost:8080
	@set -a && . ./.env && set +a && uv run dbt docs generate --project-dir dbt --profiles-dir dbt && \
		uv run dbt docs serve --project-dir dbt --profiles-dir dbt --port 8080

dashboard: ## Start the Streamlit dashboard at http://localhost:8501
	uv run streamlit run src/uk_grid/dashboard/app.py

lint: ## Lint Python code with ruff
	uv run ruff check src tests

format: ## Format Python code with ruff
	uv run ruff format src tests

clean: ## Remove dbt target, dbt packages, dagster storage
	rm -rf dbt/target/ dbt/dbt_packages/ logs/ .dagster_home/
