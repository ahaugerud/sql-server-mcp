from unittest.mock import patch

import pytest

from sql_server_mcp.db import ensure_odbc_driver_available


def test_ensure_odbc_driver_available_passes_when_driver_present():
    with patch(
        "sql_server_mcp.db.pyodbc.drivers",
        return_value=["ODBC Driver 18 for SQL Server"],
    ):
        ensure_odbc_driver_available("{ODBC Driver 18 for SQL Server}")


def test_ensure_odbc_driver_available_raises_when_missing():
    with patch("sql_server_mcp.db.pyodbc.drivers", return_value=[]):
        with pytest.raises(ConnectionError):
            ensure_odbc_driver_available("{ODBC Driver 18 for SQL Server}")
