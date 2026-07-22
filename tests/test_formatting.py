from datetime import date, datetime

from sql_server_mcp.formatting import format_markdown_table, format_value


def test_format_value_handles_none():
    assert format_value(None) == "null"


def test_format_value_handles_datetime_and_date():
    assert format_value(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05"
    assert format_value(date(2026, 1, 2)) == "2026-01-02"


def test_format_value_handles_bool():
    assert format_value(True) == "true"
    assert format_value(False) == "false"


def test_format_value_handles_list():
    assert format_value([1, 2, 3]) == "1, 2, 3"


def test_format_value_handles_plain_values():
    assert format_value("hello") == "hello"
    assert format_value(42) == "42"


def test_format_markdown_table_empty_rows():
    result = format_markdown_table([], "Query Results")
    assert result == "# Query Results\n\nNo results found."


def test_format_markdown_table_basic_shape():
    rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    result = format_markdown_table(rows, "Query Results")
    assert "# Query Results" in result
    assert "| id | name |" in result
    assert "| --- | --- |" in result
    assert "| 1 | Alice |" in result
    assert "| 2 | Bob |" in result


def test_format_markdown_table_escapes_pipe_in_cell_values():
    rows = [{"id": 1, "note": "a | b"}]
    result = format_markdown_table(rows, "Query Results")
    assert "a \\| b" in result


def test_format_markdown_table_strips_newlines_in_cell_values():
    rows = [{"id": 1, "note": "line1\nline2"}]
    result = format_markdown_table(rows, "Query Results")
    assert "| 1 | line1 line2 |" in result


def test_format_markdown_table_handles_none_values():
    rows = [{"id": 1, "note": None}]
    result = format_markdown_table(rows, "Query Results")
    assert "| 1 | null |" in result
