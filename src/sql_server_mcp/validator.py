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


def _is_readonly_query(node: exp.Expression | None) -> bool:
    if isinstance(node, exp.Subquery):
        return _is_readonly_query(node.this)
    if isinstance(node, exp.SetOperation):  # UNION, INTERSECT, EXCEPT
        return _is_readonly_query(node.left) and _is_readonly_query(node.right)
    return isinstance(node, exp.Select)


def is_readonly(statements: list[exp.Expression]) -> bool:
    """True only if every statement is a SELECT, or a UNION/INTERSECT/EXCEPT
    of SELECTs (a `WITH ... SELECT` parses as a single exp.Select with the
    CTEs attached)."""
    if not statements:
        return False

    return all(_is_readonly_query(stmt) for stmt in statements)


def apply_row_limit(
    statement: exp.Select | exp.SetOperation, max_rows: int
) -> exp.Select | exp.SetOperation:
    """Cap `statement` to at most `max_rows` rows, returning the capped
    statement (mutated in place, except a set operation without ORDER BY,
    which is wrapped in a new outer SELECT). Leaves an existing TOP/LIMIT
    untouched."""
    if max_rows <= 0:
        raise ValueError("max_rows must be a positive integer.")

    target = statement
    if isinstance(statement, exp.SetOperation):
        # For T-SQL, sqlglot attaches a trailing ORDER BY / OFFSET / FETCH to
        # the right-most SELECT (OFFSET may land on the set operation itself),
        # but in T-SQL they apply to the combined result.
        target = statement
        while isinstance(target, exp.SetOperation):
            target = target.expression
        if not isinstance(target, exp.Select):
            return _wrap_in_top(statement, max_rows)
        if target.args.get("limit") is not None:
            return statement
        if target.args.get("order") is None:
            return _wrap_in_top(statement, max_rows)
        offset = statement.args.pop("offset", None)
        if offset is not None:
            target.set("offset", offset)
    elif statement.args.get("limit") is not None:
        return statement

    if target.args.get("order") is not None and target.args.get("offset") is None:
        # T-SQL requires OFFSET/FETCH rather than bare TOP alongside ORDER BY
        target.set("offset", exp.Offset(expression=exp.Literal.number(0)))

    target.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
    return statement


def _wrap_in_top(statement: exp.Expression, max_rows: int) -> exp.Select:
    return (
        exp.select(exp.Star())
        .from_(statement.subquery("_limited"))
        .limit(max_rows)
    )
