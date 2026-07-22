"""pyodbc connection factory for AAD-token-authenticated connections."""

from __future__ import annotations

import struct

import pyodbc

# https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory
SQL_SERVER_SCOPE = "https://database.windows.net/.default"

# SQL_COPT_SS_ACCESS_TOKEN, defined in msodbcsql.h
SQL_COPT_SS_ACCESS_TOKEN = 1256

DEFAULT_ODBC_DRIVER = "{ODBC Driver 18 for SQL Server}"


def ensure_odbc_driver_available(odbc_driver: str = DEFAULT_ODBC_DRIVER) -> None:
    """Raise ConnectionError if `odbc_driver` isn't installed."""
    driver_name = odbc_driver.strip("{}")
    available = pyodbc.drivers()
    if driver_name not in available:
        raise ConnectionError(
            f"ODBC driver {driver_name!r} is not installed on this machine "
            f"(available drivers: {available or 'none found'}). Install the "
            "Microsoft ODBC Driver 18 for SQL Server: "
            "https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server"
        )


def build_token_struct(access_token: str) -> bytes:
    """Pack an AAD access token into the struct pyodbc requires.

    Format: 4-byte little-endian length prefix + UTF-16-LE encoded token.
    """
    token_bytes = access_token.encode("utf-16-le")
    return struct.pack(f"<i{len(token_bytes)}s", len(token_bytes), token_bytes)


def connect(
    server: str,
    database: str,
    access_token: str,
    odbc_driver: str = DEFAULT_ODBC_DRIVER,
    timeout_seconds: int = 30,
) -> pyodbc.Connection:
    """Open a new pyodbc connection authenticated with `access_token`."""
    conn_str = (
        f"DRIVER={odbc_driver};SERVER={server};DATABASE={database};"
        f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout={timeout_seconds};"
    )
    token_struct = build_token_struct(access_token)

    try:
        return pyodbc.connect(
            conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
        )
    except pyodbc.Error as db_err:
        raise ConnectionError(f"Database connection failed: {db_err}") from db_err
