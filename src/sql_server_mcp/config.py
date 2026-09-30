"""Server configuration, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    sql_server_name: str
    sql_database_name: str
    tenant_id: str | None = None
    username: str | None = None
    password: str | None = None
    max_rows: int = 25
    trust_server_certificate: bool = False

    @property
    def uses_sql_login(self) -> bool:
        return self.username is not None


def load_settings() -> Settings:
    server_name = os.getenv("MCP_SQL_SERVER_NAME")
    database_name = os.getenv("MCP_SQL_DATABASE_NAME")
    tenant_id = os.getenv("MCP_AZURE_TENANT_ID") or None
    username = os.getenv("MCP_SQL_USERNAME") or None
    password = os.getenv("MCP_SQL_PASSWORD") or None

    if (username is None) != (password is None):
        raise ConfigError(
            "MCP_SQL_USERNAME and MCP_SQL_PASSWORD must be set together."
        )

    required = [
        ("MCP_SQL_SERVER_NAME", server_name),
        ("MCP_SQL_DATABASE_NAME", database_name),
    ]
    if username is None:
        # Entra ID auth needs the tenant; SQL login does not.
        required.append(("MCP_AZURE_TENANT_ID", tenant_id))
    missing = [var_name for var_name, value in required if not value]
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

    trust_raw = os.getenv("MCP_SQL_TRUST_SERVER_CERTIFICATE", "false").strip().lower()
    if trust_raw in ("1", "true", "yes"):
        trust_server_certificate = True
    elif trust_raw in ("", "0", "false", "no"):
        trust_server_certificate = False
    else:
        raise ConfigError(
            "MCP_SQL_TRUST_SERVER_CERTIFICATE must be true or false, "
            f"got {trust_raw!r}"
        )

    return Settings(
        sql_server_name=server_name,  # type: ignore[arg-type]
        sql_database_name=database_name,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        username=username,
        password=password,
        max_rows=max_rows,
        trust_server_certificate=trust_server_certificate,
    )
