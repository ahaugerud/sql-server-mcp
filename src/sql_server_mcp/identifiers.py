"""Allow-listing for SQL identifiers - unlike literal values, identifiers
can't be bound as query parameters, so they're validated before use."""

from __future__ import annotations

import re

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")


class InvalidIdentifierError(ValueError):
    """Raised when a proposed database/schema/table name fails the allow-list."""


def validate_identifier(name: str) -> str:
    """Return `name` if it contains only letters, digits, and underscores."""
    if not name or not _IDENTIFIER_RE.match(name):
        raise InvalidIdentifierError(
            f"{name!r} is not a valid identifier: only letters, digits, "
            "and underscores are allowed."
        )
    return name
