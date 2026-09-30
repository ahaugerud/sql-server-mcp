"""mssql-python connection factory (AAD token or SQL username/password)."""

from __future__ import annotations

import mssql_python
from azure.core.credentials import TokenCredential

# https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory
SQL_SERVER_SCOPE = "https://database.windows.net/.default"


def connect(
    server: str,
    database: str,
    credential: TokenCredential | None = None,
    timeout_seconds: int = 30,
    username: str | None = None,
    password: str | None = None,
) -> mssql_python.Connection:
    """Open a new mssql-python connection.

    With `username`/`password`, uses SQL authentication. Otherwise authenticates
    as `credential`; mssql-python calls `credential.get_token(SQL_SERVER_SCOPE)`
    itself, so no token needs to be acquired up front.
    """
    conn_str = f"Server={server};Database={database};Encrypt=yes;TrustServerCertificate=no;"

    try:
        if username is not None:
            conn_str += f"UID={_escape(username)};PWD={_escape(password or '')};"
            return mssql_python.connect(conn_str, timeout=timeout_seconds)
        if credential is None:
            raise ValueError("Either a credential or username/password is required.")
        return mssql_python.connect(
            conn_str, token_provider=credential, timeout=timeout_seconds
        )
    except mssql_python.Error as db_err:
        raise ConnectionError(f"Database connection failed: {db_err}") from db_err


def _escape(value: str) -> str:
    """Brace-quote a connection string value so `;` and `}` are safe."""
    return "{" + value.replace("}", "}}") + "}"
