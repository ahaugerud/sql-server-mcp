"""
Manual smoke test against a real database - not part of the automated
pytest suite (needs a real network connection and login).

Usage:
    export MCP_SQL_SERVER_NAME=your-server.datawarehouse.fabric.microsoft.com
    export MCP_SQL_DATABASE_NAME=your_database
    export MCP_AZURE_TENANT_ID=your-tenant-id
    uv run python scripts/manual_smoke_test.py
"""

from __future__ import annotations

import asyncio
import sys

from fastmcp import Client

from sql_server_mcp.config import ConfigError, load_settings
from sql_server_mcp.credentials import build_credential
from sql_server_mcp.db import ensure_odbc_driver_available
from sql_server_mcp.server import create_app


async def run_smoke_test() -> None:
    try:
        settings = load_settings()
        ensure_odbc_driver_available(settings.odbc_driver)
        credential = build_credential(settings.tenant_id)
    except (ConfigError, ConnectionError) as exc:
        sys.stderr.write(f"Startup failed: {exc}\n")
        sys.exit(1)

    app = create_app(settings, credential)

    async with Client(app) as client:
        print("--- list_databases ---")
        result = await client.call_tool("list_databases", {})
        print(result.data)

        print("\n--- search_schema (tables, wildcard '*', first database only) ---")
        result = await client.call_tool(
            "search_schema",
            {
                "target": "tables",
                "name": "*",
                "databases": [settings.sql_database_name],
            },
        )
        print(result.data)

        print("\n--- query (SELECT 1) ---")
        result = await client.call_tool("query", {"sql": "SELECT 1 AS smoke_test"})
        print(result.data)

        print("\n--- export_query (parquet) ---")
        result = await client.call_tool(
            "export_query",
            {
                "sql": (
                    f"SELECT * FROM {settings.sql_database_name}."
                    "INFORMATION_SCHEMA.TABLES"
                ),
                "path": "/tmp/smoke_test_export.parquet",
            },
        )
        print(result.data)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
