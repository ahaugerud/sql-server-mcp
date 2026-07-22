"""FastMCP server: query, list_databases, search_schema tools."""

from __future__ import annotations

from typing import Any, Literal

from azure.core.credentials import TokenCredential
from fastmcp import FastMCP

from sql_server_mcp import db
from sql_server_mcp.config import Settings
from sql_server_mcp.credentials import get_access_token
from sql_server_mcp.export import write_csv, write_parquet
from sql_server_mcp.formatting import format_markdown_table
from sql_server_mcp.schema_queries import (
    build_list_databases_query,
    build_search_schema_query,
)
from sql_server_mcp.validator import (
    SqlValidationError,
    apply_row_limit,
    is_readonly,
    parse_statements,
)


def _execute(
    settings: Settings,
    access_token: str,
    expression: Any,
    params: list[str] | None = None,
) -> list[dict[str, Any]]:
    sql_text = expression.sql(dialect="tsql")
    conn = db.connect(
        settings.sql_server_name,
        settings.sql_database_name,
        access_token,
        settings.odbc_driver,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(sql_text, params) if params else cursor.execute(sql_text)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def create_app(settings: Settings, credential: TokenCredential) -> FastMCP:
    app = FastMCP("sql-server-mcp")

    @app.tool(
        name="query",
        description=(
            f"Execute a single read-only SELECT statement. Returns at most "
            f"{settings.max_rows} rows. Table references must be fully "
            f"qualified as database.schema.table - there is no mutable "
            f"'active database'."
        ),
    )
    async def query(sql: str) -> str:
        statements = parse_statements(sql)
        if len(statements) != 1:
            raise SqlValidationError(
                "Only a single SELECT statement is supported per call."
            )
        if not is_readonly(statements):
            raise SqlValidationError("Only read-only SELECT statements are allowed.")

        limited = apply_row_limit(statements[0], settings.max_rows)
        rows = _execute(settings, get_access_token(credential), limited)
        return format_markdown_table(rows, "Query Results")

    @app.tool(
        name="list_databases",
        description=(
            f"List all user databases with status and metadata. Returns at "
            f"most {settings.max_rows} rows."
        ),
    )
    async def list_databases() -> str:
        limited = apply_row_limit(build_list_databases_query(), settings.max_rows)
        rows = _execute(settings, get_access_token(credential), limited)
        return format_markdown_table(rows, "Databases")

    @app.tool(
        name="search_schema",
        description=(
            f"Search table or column metadata across databases via "
            f"INFORMATION_SCHEMA. Omit `databases` to search every database "
            f"on the server. Returns at most {settings.max_rows} rows."
        ),
    )
    async def search_schema(
        target: Literal["tables", "columns"],
        name: str,
        databases: list[str] | None = None,
        schema: str | None = None,
        use_wildcard: bool = True,
    ) -> str:
        access_token = get_access_token(credential)

        target_databases = databases
        if not target_databases:
            # not row-capped: used to build the search below, not returned directly
            db_rows = _execute(settings, access_token, build_list_databases_query())
            target_databases = [row["database_name"] for row in db_rows]

        schema_query = build_search_schema_query(
            target, target_databases, name, schema, use_wildcard
        )
        limited = apply_row_limit(schema_query.expression, settings.max_rows)
        rows = _execute(settings, access_token, limited, schema_query.params)
        title = "Table Search Results" if target == "tables" else "Column Search Results"
        return format_markdown_table(rows, title)

    @app.tool(
        name="export_query",
        description=(
            "Execute a single read-only SELECT statement and write the full, "
            "uncapped result to a local Parquet or CSV file instead of "
            "returning it. Use this instead of `query` for large results or "
            "when the output will be processed by other local tools."
        ),
    )
    async def export_query(
        sql: str, path: str, format: Literal["parquet", "csv"] = "parquet"
    ) -> str:
        statements = parse_statements(sql)
        if len(statements) != 1:
            raise SqlValidationError(
                "Only a single SELECT statement is supported per call."
            )
        if not is_readonly(statements):
            raise SqlValidationError("Only read-only SELECT statements are allowed.")

        rows = _execute(settings, get_access_token(credential), statements[0])
        if not rows:
            return "Query returned 0 rows; no file was written."

        (write_parquet if format == "parquet" else write_csv)(rows, path)
        return f"Wrote {len(rows)} rows to {path}\nColumns: {', '.join(rows[0].keys())}"

    return app
