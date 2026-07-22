"""Server configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from sql_server_mcp.db import DEFAULT_ODBC_DRIVER


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    sql_server_name: str
    sql_database_name: str
    tenant_id: str
    max_rows: int = 25
    odbc_driver: str = DEFAULT_ODBC_DRIVER


def load_settings() -> Settings:
    server_name = os.getenv("MCP_SQL_SERVER_NAME")
    database_name = os.getenv("MCP_SQL_DATABASE_NAME")
    tenant_id = os.getenv("MCP_AZURE_TENANT_ID")

    missing = [
        var_name
        for var_name, value in (
            ("MCP_SQL_SERVER_NAME", server_name),
            ("MCP_SQL_DATABASE_NAME", database_name),
            ("MCP_AZURE_TENANT_ID", tenant_id),
        )
        if not value
    ]
    if missing:
        raise ConfigError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )

    max_rows_raw = os.getenv("MCP_MAX_ROWS", "25")
    try:
        max_rows = int(max_rows_raw)
    except ValueError as exc:
        raise ConfigError(f"MCP_MAX_ROWS must be an integer, got {max_rows_raw!r}") from exc
    if max_rows <= 0:
        raise ConfigError("MCP_MAX_ROWS must be a positive integer.")

    return Settings(
        sql_server_name=server_name,  # type: ignore[arg-type]
        sql_database_name=database_name,  # type: ignore[arg-type]
        tenant_id=tenant_id,  # type: ignore[arg-type]
        max_rows=max_rows,
        odbc_driver=os.getenv("ODBC_DRIVER", DEFAULT_ODBC_DRIVER),
    )
