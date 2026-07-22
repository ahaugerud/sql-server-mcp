"""Markdown-Table result formatting."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


def format_value(value: Any) -> str:
    """Format a single cell value as a string."""
    if value is None:
        return "null"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return str(value)
    return str(value)


def _escape_cell(value: str) -> str:
    """Escape characters that would otherwise break Markdown table syntax."""
    return value.replace("|", "\\|").replace("\n", " ").replace("\r", "")


def format_markdown_table(rows: list[dict[str, Any]], title: str) -> str:
    """Render `rows` as a Markdown table under a `# title` heading."""
    if not rows:
        return f"# {title}\n\nNo results found."

    columns = list(rows[0].keys())
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"

    body_lines = []
    for row in rows:
        cells = [_escape_cell(format_value(row.get(col))) for col in columns]
        body_lines.append("| " + " | ".join(cells) + " |")

    table = "\n".join([header, separator, *body_lines])
    return f"# {title}\n\n{table}"
