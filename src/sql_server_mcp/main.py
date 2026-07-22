"""Entrypoint - see README.md for configuration."""

import sys

from azure.core.exceptions import ClientAuthenticationError

from sql_server_mcp.config import ConfigError, load_settings
from sql_server_mcp.credentials import build_credential
from sql_server_mcp.db import ensure_odbc_driver_available
from sql_server_mcp.server import create_app


def main() -> None:
    try:
        settings = load_settings()
        ensure_odbc_driver_available(settings.odbc_driver)
        credential = build_credential(settings.tenant_id)
    except (ConfigError, ConnectionError, ClientAuthenticationError) as exc:
        sys.stderr.write(f"Startup failed: {exc}\n")
        sys.exit(1)

    app = create_app(settings, credential)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
