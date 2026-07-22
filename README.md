# sql-server-mcp

A local MCP server for read-only SQL Server / MS Fabric queries. Runs as a
single-user process over stdio, authenticated as *you* (delegated Entra ID
identity, not a service principal) — **one server process per
tenant**. 

## Prerequisites

- Python 3.14+ and [uv](https://docs.astral.sh/uv/)
- [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) installed on your machine
- Either the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) logged in to the target tenant (`az login --tenant <tenant-id>`), or just a browser available — the server falls back to an interactive browser login if there's no CLI session
- An Entra ID account in the target tenant with read access to the target database (e.g. `db_datareader`)

## Configuration

Each tenant gets its own set of environment variables:

| Variable | Required | Description |
|---|---|---|
| `MCP_SQL_SERVER_NAME` | yes | SQL Server / Fabric SQL endpoint hostname, e.g. `xyz-xyz.datawarehouse.fabric.microsoft.com` |
| `MCP_SQL_DATABASE_NAME` | yes | Default database to connect to |
| `MCP_AZURE_TENANT_ID` | yes | The Entra ID tenant ID — pins auth to this directory even if your machine has other `az login` sessions active |
| `MCP_MAX_ROWS` | no | Max rows returned per tool call (default: 25) |
| `ODBC_DRIVER` | no | ODBC driver name (default: `ODBC Driver 18 for SQL Server`) |

## Running it

The server is a `uvx`-runnable console script (`sql-server-mcp`), no
manual install step needed - `uvx` builds an isolated environment for it
on first run and reuses it afterwards:

```bash
uvx sql-server-mcp
```

To run from a local checkout instead (e.g. during development), point
`--from` at the path:

```bash
uvx --from /path/to/sql-server-mcp sql-server-mcp
```

On startup it checks the ODBC driver is installed, then acquires a token
(via `az login` if available, otherwise an interactive browser prompt) and
runs over stdio.

### Example MCP client config

One block per tenant:

```json
{
  "mcpServers": {
    "tenant-a-sql": {
      "command": "uvx",
      "args": ["sql-server-mcp"],
      "env": {
        "MCP_SQL_SERVER_NAME": "tenant-a.datawarehouse.fabric.microsoft.com",
        "MCP_SQL_DATABASE_NAME": "wh_silver",
        "MCP_AZURE_TENANT_ID": "<tenant-a-tenant-id>"
      }
    },
    "tenant-b-sql": {
      "command": "uvx",
      "args": ["sql-server-mcp"],
      "env": {
        "MCP_SQL_SERVER_NAME": "tenant-b.datawarehouse.fabric.microsoft.com",
        "MCP_SQL_DATABASE_NAME": "wh_gold",
        "MCP_AZURE_TENANT_ID": "<tenant-b-tenant-id>"
      }
    }
  }
}
```

## Tools

- **`query(sql)`** — run a single read-only `SELECT`. Table references must be fully qualified as `database.schema.table`; there's no mutable "active database". Returns at most `MCP_MAX_ROWS` rows, as a Markdown table.
- **`list_databases()`** — list user databases with status/metadata.
- **`search_schema(target, name, databases?, schema?, use_wildcard?)`** — search table or column metadata via `INFORMATION_SCHEMA` across one or more databases (all of them if `databases` is omitted).
- **`export_query(sql, path, format?)`** — run a single read-only `SELECT` and write the full, uncapped result to a local Parquet or CSV file instead of returning it. For large results or when the output feeds into other local tools (pandas, DuckDB, etc.).

## Development

```bash
uv run pytest          # unit tests, no network/DB/Azure required
uv run python scripts/manual_smoke_test.py   # real end-to-end check against a live database
```
