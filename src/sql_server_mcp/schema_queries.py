"""Cross-database INFORMATION_SCHEMA search, built via sqlglot expressions
and UNION ALL rather than dynamic SQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from sqlglot import exp

from sql_server_mcp.identifiers import validate_identifier

_TABLES_COLUMNS = ("TABLE_CATALOG", "TABLE_SCHEMA", "TABLE_NAME", "TABLE_TYPE")
_COLUMNS_COLUMNS = (
    "TABLE_CATALOG",
    "TABLE_SCHEMA",
    "TABLE_NAME",
    "COLUMN_NAME",
    "ORDINAL_POSITION",
    "DATA_TYPE",
)

_SYSTEM_DATABASES = ("master", "tempdb", "model", "msdb")


@dataclass(frozen=True)
class SchemaQuery:
    """A generated query paired with the params to bind to it, in order."""

    expression: exp.Query
    params: list[str]


def _information_schema_table(database: str, view: Literal["TABLES", "COLUMNS"]) -> exp.Table:
    return exp.Table(
        this=exp.to_identifier(view),
        db=exp.to_identifier("INFORMATION_SCHEMA"),
        catalog=exp.to_identifier(database, quoted=True),
    )


def build_list_databases_query() -> exp.Select:
    """List user databases with status and metadata, excluding system databases."""
    state_case = exp.Case(
        this=exp.column("state"),
        ifs=[
            exp.If(this=exp.Literal.number(n), true=exp.Literal.string(label))
            for n, label in (
                (0, "ONLINE"),
                (1, "RESTORING"),
                (2, "RECOVERING"),
                (3, "RECOVERY_PENDING"),
                (4, "SUSPECT"),
                (5, "EMERGENCY"),
                (6, "OFFLINE"),
                (7, "COPYING"),
                (10, "OFFLINE_SECONDARY"),
            )
        ],
        default=exp.Literal.string("UNKNOWN"),
    )

    return (
        exp.select(
            exp.column("name").as_("database_name"),
            "database_id",
            "create_date",
            state_case.as_("state"),
            "collation_name",
            "compatibility_level",
        )
        .from_("sys.databases")
        .where(exp.column("name").isin(*_SYSTEM_DATABASES).not_())
        .order_by("name")
    )


def build_search_schema_query(
    target: Literal["tables", "columns"],
    databases: Sequence[str],
    name_filter: str,
    schema_filter: str | None = None,
    use_wildcard: bool = True,
) -> SchemaQuery:
    """Build a cross-database search over INFORMATION_SCHEMA.TABLES/COLUMNS."""
    if not databases:
        raise ValueError("At least one database must be specified.")

    validated_dbs = [validate_identifier(db) for db in databases]
    view: Literal["TABLES", "COLUMNS"] = "TABLES" if target == "tables" else "COLUMNS"
    name_column = "TABLE_NAME" if target == "tables" else "COLUMN_NAME"
    select_columns = _TABLES_COLUMNS if target == "tables" else _COLUMNS_COLUMNS

    comparator = "LIKE" if use_wildcard else "="
    if use_wildcard and name_filter in ("*", ""):
        filter_value = "%"
    elif use_wildcard:
        filter_value = f"%{name_filter}%"
    else:
        filter_value = name_filter

    params: list[str] = []
    branches: list[exp.Select] = []

    for db in validated_dbs:
        select = exp.select(
            exp.Literal.string(db).as_("DatabaseName"),
            *(exp.column(col).as_(col) for col in select_columns),
        ).from_(_information_schema_table(db, view))
        select = select.where(f"LOWER({name_column}) {comparator} LOWER(?)")
        params.append(filter_value)

        if schema_filter:
            select = select.where("TABLE_SCHEMA = ?")
            params.append(schema_filter)

        branches.append(select)

    combined: exp.Query = branches[0]
    for branch in branches[1:]:
        combined = combined.union(branch, distinct=False)

    ordered = exp.select("*").from_(combined.subquery("combined")).order_by(
        "DatabaseName", "TABLE_SCHEMA", "TABLE_NAME"
    )

    return SchemaQuery(expression=ordered, params=params)
