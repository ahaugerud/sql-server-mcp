"""Unit tests for validator.py."""

import pytest

from sql_server_mcp.validator import (
    SqlValidationError,
    apply_row_limit,
    is_readonly,
    parse_statements,
)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT * FROM foo WHERE x = 1",
        "WITH cte AS (SELECT 1 AS x) SELECT * FROM cte",
        "WITH a AS (SELECT 1 AS x), b AS (SELECT * FROM a) SELECT * FROM b",
        "SELECT TOP 5 * FROM foo ORDER BY x",
        "-- a leading comment\nSELECT 1",
    ],
)
def test_is_readonly_accepts_select_variants(sql):
    assert is_readonly(parse_statements(sql)) is True


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO foo VALUES (1)",
        "UPDATE foo SET x = 1",
        "DELETE FROM foo",
        "DROP TABLE foo",
        "ALTER TABLE foo ADD x INT",
        "TRUNCATE TABLE foo",
        "EXEC sp_executesql @sql",
        "EXECUTE sp_who",
        "GRANT SELECT ON foo TO bar",
        "REVOKE SELECT ON foo FROM bar",
        "SELECT 1; DROP TABLE foo;",
        "DROP TABLE foo; SELECT 1;",
    ],
)
def test_is_readonly_rejects_everything_except_select(sql):
    assert is_readonly(parse_statements(sql)) is False


def test_parse_statements_rejects_empty_input():
    with pytest.raises(SqlValidationError):
        parse_statements("")
    with pytest.raises(SqlValidationError):
        parse_statements("   ")


def test_parse_statements_rejects_unparseable_input():
    with pytest.raises(SqlValidationError):
        parse_statements("SELECT FROM WHERE (((")


def test_apply_row_limit_injects_top_when_no_order_by():
    (stmt,) = parse_statements("SELECT a, b FROM foo WHERE a > 1")
    limited = apply_row_limit(stmt, 25)
    sql = limited.sql(dialect="tsql")
    assert "TOP 25" in sql


def test_apply_row_limit_uses_offset_fetch_when_order_by_present():
    (stmt,) = parse_statements("SELECT a, b FROM foo ORDER BY a")
    limited = apply_row_limit(stmt, 25)
    sql = limited.sql(dialect="tsql")
    assert "OFFSET" in sql and "FETCH" in sql
    assert "25" in sql


def test_apply_row_limit_leaves_existing_top_alone():
    (stmt,) = parse_statements("SELECT TOP 10 a FROM foo")
    limited = apply_row_limit(stmt, 25)
    sql = limited.sql(dialect="tsql")
    assert "TOP 10" in sql
    assert "TOP 25" not in sql


def test_apply_row_limit_rejects_non_positive_max_rows():
    (stmt,) = parse_statements("SELECT 1")
    with pytest.raises(ValueError):
        apply_row_limit(stmt, 0)
