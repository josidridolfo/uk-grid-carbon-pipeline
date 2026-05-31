"""Shared Dagster resources: Snowflake I/O manager, settings."""

from __future__ import annotations

import dagster as dg
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from snowflake.connector.pandas_tools import write_pandas

load_dotenv()


class Settings(BaseSettings):
    """Project-wide settings, loaded from environment variables and .env."""

    # Snowflake connection
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_private_key_path: str | None = None
    snowflake_private_key_passphrase: str | None = None
    snowflake_role: str = "TRANSFORMER"
    snowflake_warehouse: str = "TRANSFORMING"
    snowflake_database: str = "UK_GRID"
    snowflake_schema: str = "RAW"

    # Other
    met_office_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


class UKGridSnowflakeIOManager(dg.IOManager):
    """Custom Snowflake I/O manager for pandas DataFrames.

    Why this exists (and not ``dagster_snowflake_pandas.SnowflakePandasIOManager``):
    Dagster's ``ConfigurableIOManager`` is a Pydantic model that gets re-instantiated
    via ``model_validate`` by Dagster's config-resolution layer at materialise time.
    When the IO manager is constructed via direct kwargs from a Settings singleton
    (rather than via Dagster's ``EnvVar`` references), this re-instantiation drops
    the in-memory config and the Snowflake driver receives empty credentials —
    which Snowflake surfaces as a misleading ``250001 Incorrect username or password``
    error even though the credentials in ``.env`` are perfectly valid.

    This custom ``IOManager`` subclass holds a ``Settings`` reference directly and
    bypasses the config-resolution layer entirely. Roughly 50 lines, no Pydantic
    surface area, predictable at materialise time. The trade-off: assets must
    return ``pandas.DataFrame``; per-asset schema overrides use the same
    ``metadata={"schema": "..."}`` pattern that ``SnowflakePandasIOManager`` uses,
    so existing asset decorators do not need changes.
    """

    def __init__(self, project_settings: Settings) -> None:
        self._settings = project_settings

    def _connect_kwargs(self, schema: str) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "account": self._settings.snowflake_account,
            "user": self._settings.snowflake_user,
            "role": self._settings.snowflake_role,
            "warehouse": self._settings.snowflake_warehouse,
            "database": self._settings.snowflake_database,
            "schema": schema,
        }
        if self._settings.snowflake_private_key_path:
            kwargs["private_key_path"] = self._settings.snowflake_private_key_path
            if self._settings.snowflake_private_key_passphrase:
                kwargs["private_key_passphrase"] = (
                    self._settings.snowflake_private_key_passphrase
                )
        else:
            kwargs["password"] = self._settings.snowflake_password
        return kwargs

    def _resolve_schema(self, context: dg.OutputContext | dg.InputContext) -> str:
        """Per-asset schema override via ``metadata={"schema": "..."}`` on the asset decorator."""
        meta = getattr(context, "definition_metadata", None) or {}
        override = meta.get("schema")
        if override is not None:
            return str(override.value if hasattr(override, "value") else override)
        return self._settings.snowflake_schema

    @staticmethod
    def _table_name(asset_key: dg.AssetKey) -> str:
        """Asset key's last segment becomes the Snowflake table name (uppercased)."""
        return asset_key.path[-1].upper()

    def handle_output(
        self, context: dg.OutputContext, obj: pd.DataFrame | None
    ) -> None:
        if obj is None:
            context.log.warning(f"Output is None for {context.asset_key}; skipping write")
            return
        if not isinstance(obj, pd.DataFrame):
            raise TypeError(
                f"UKGridSnowflakeIOManager expects pandas.DataFrame; got {type(obj).__name__}"
            )
        if len(obj) == 0:
            context.log.warning(f"Empty DataFrame for {context.asset_key}; skipping write")
            return

        schema = self._resolve_schema(context)
        table = self._table_name(context.asset_key)
        fqn = f"{self._settings.snowflake_database}.{schema}.{table}"

        context.log.info(f"Writing {len(obj)} rows to {fqn}")

        with snowflake.connector.connect(**self._connect_kwargs(schema)) as conn:
            # Idempotent: TRANSFORMER has CREATE SCHEMA on the database.
            conn.cursor().execute(
                f"CREATE SCHEMA IF NOT EXISTS {self._settings.snowflake_database}.{schema}"
            )
            success, _, nrows, _ = write_pandas(
                conn=conn,
                df=obj,
                table_name=table,
                auto_create_table=True,
                overwrite=True,
                quote_identifiers=False,
                # use_logical_type=True ensures tz-aware pandas datetimes land as
                # Snowflake TIMESTAMP_TZ rather than NUMBER-of-nanoseconds.
                use_logical_type=True,
            )
            if not success:
                raise RuntimeError(f"write_pandas reported failure for {fqn}")

        context.log.info(f"Wrote {nrows} rows to {fqn}")
        context.add_output_metadata(
            {
                "snowflake_table": fqn,
                "rows_written": nrows,
            }
        )

    def load_input(self, context: dg.InputContext) -> pd.DataFrame:
        upstream = context.upstream_output
        if upstream is None:
            raise ValueError(
                "UKGridSnowflakeIOManager.load_input called without upstream context"
            )

        schema = self._resolve_schema(upstream)
        table = self._table_name(upstream.asset_key)
        fqn = f"{self._settings.snowflake_database}.{schema}.{table}"

        with snowflake.connector.connect(**self._connect_kwargs(schema)) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM {fqn}")
                return cursor.fetch_pandas_all()
            finally:
                cursor.close()


def get_snowflake_io_manager() -> UKGridSnowflakeIOManager:
    """Factory for the custom Snowflake IO manager.

    Returned instance is passed directly into ``Definitions(resources={...})``;
    it is not wrapped by ``ConfigurableIOManager`` and therefore retains its
    in-memory ``Settings`` reference at materialise time. See the class
    docstring for the root cause this works around.
    """
    return UKGridSnowflakeIOManager(settings)
