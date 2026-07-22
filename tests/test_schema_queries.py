import pytest

from sql_server_mcp.identifiers import InvalidIdentifierError
from sql_server_mcp.schema_queries import (
    build_list_databases_query,
    build_search_schema_query,
)


def test_list_databases_query_excludes_system_databases():
    sql = build_list_databases_query().sql(dialect="tsql")
    assert "sys.databases" in sql
    for system_db in ("master", "tempdb", "model", "msdb"):
        assert system_db in sql  # present in the exclusion list
    assert "NOT" in sql.upper() or "NOT IN" in sql.upper()


def test_search_schema_rejects_malicious_database_name():
    with pytest.raises(InvalidIdentifierError):
        build_search_schema_query(
            "tables", ["foo]; DROP TABLE bar; --"], "customer"
        )


def test_search_schema_never_interpolates_the_search_term_into_sql_text():
    injection_attempt = "x' UNION SELECT name, name, name, name FROM sys.tables --"
    query = build_search_schema_query("tables", ["Sales"], injection_attempt)
    sql = query.expression.sql(dialect="tsql")
    # The search term must appear only as a bound parameter, never as SQL text.
    assert injection_attempt not in sql
    assert query.params == ["%" + injection_attempt + "%"]


def test_search_schema_single_database_tables():
    query = build_search_schema_query("tables", ["Sales"], "customer")
    sql = query.expression.sql(dialect="tsql")
    assert "[Sales].INFORMATION_SCHEMA.TABLES" in sql
    assert "UNION ALL" not in sql
    assert query.params == ["%customer%"]


def test_search_schema_multi_database_union_all():
    query = build_search_schema_query(
        "tables", ["Sales", "Staging", "Prod"], "customer"
    )
    sql = query.expression.sql(dialect="tsql")
    assert sql.count("UNION ALL") == 2
    for db in ("Sales", "Staging", "Prod"):
        assert f"[{db}].INFORMATION_SCHEMA.TABLES" in sql
    assert query.params == ["%customer%"] * 3


def test_search_schema_columns_target_uses_columns_view():
    query = build_search_schema_query("columns", ["Sales"], "id")
    sql = query.expression.sql(dialect="tsql")
    assert "INFORMATION_SCHEMA.COLUMNS" in sql
    assert "COLUMN_NAME" in sql


def test_search_schema_schema_filter_adds_bound_param():
    query = build_search_schema_query(
        "tables", ["Sales"], "customer", schema_filter="dbo"
    )
    assert query.params == ["%customer%", "dbo"]
    assert "TABLE_SCHEMA = ?" in query.expression.sql(dialect="tsql")


def test_search_schema_exact_match_uses_equality_not_like():
    query = build_search_schema_query(
        "tables", ["Sales"], "Customer", use_wildcard=False
    )
    sql = query.expression.sql(dialect="tsql")
    assert "= LOWER(?)" in sql
    assert "LIKE" not in sql
    assert query.params == ["Customer"]


def test_search_schema_requires_at_least_one_database():
    with pytest.raises(ValueError):
        build_search_schema_query("tables", [], "customer")


def test_search_schema_wildcard_star_matches_everything():
    query = build_search_schema_query("tables", ["Sales"], "*")
    assert query.params == ["%"]
