"""sqlglot-based read-only SQL enforcement and row limiting."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

DIALECT = "tsql"


class SqlValidationError(ValueError):
    """Raised when input SQL fails to parse or is not read-only."""


def parse_statements(sql: str) -> list[exp.Expression]:
    """Parse `sql` into one or more statements."""
    if not sql or not sql.strip():
        raise SqlValidationError("SQL query is empty.")

    try:
        statements = sqlglot.parse(sql, dialect=DIALECT)
    except Exception as exc:
        raise SqlValidationError(f"Failed to parse SQL: {exc}") from exc

    # sqlglot yields None for stray empty statements, e.g. "SELECT 1;;"
    statements = [s for s in statements if s is not None]

    if not statements:
        raise SqlValidationError("SQL query contains no executable statements.")

    return statements


def is_readonly(statements: list[exp.Expression]) -> bool:
    """True only if every statement is a SELECT (a `WITH ... SELECT` parses
    as a single exp.Select with the CTEs attached)."""
    if not statements:
        return False

    return all(isinstance(stmt, exp.Select) for stmt in statements)


def apply_row_limit(statement: exp.Select, max_rows: int) -> exp.Select:
    """Cap `statement` to at most `max_rows` rows, mutating and returning it.
    Leaves an existing TOP/LIMIT untouched."""
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")

    if statement.args.get("limit") is not None:
        return statement

    if statement.args.get("order") is not None:
        # T-SQL requires OFFSET/FETCH rather than bare TOP alongside ORDER BY
        statement.set("offset", exp.Offset(expression=exp.Literal.number(0)))

    statement.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
    return statement
