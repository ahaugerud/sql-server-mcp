from unittest.mock import MagicMock, patch

import mssql_python
import pytest

from sql_server_mcp.db import connect


def test_connect_passes_credential_as_token_provider():
    fake_connection = MagicMock()
    with patch(
        "sql_server_mcp.db.mssql_python.connect", return_value=fake_connection
    ) as mock_connect:
        credential = MagicMock()
        result = connect("myserver", "mydb", credential)

        assert result is fake_connection
        args, kwargs = mock_connect.call_args
        assert "Server=myserver" in args[0]
        assert "Database=mydb" in args[0]
        assert kwargs["token_provider"] is credential


def test_connect_wraps_driver_errors_in_connection_error():
    with patch(
        "sql_server_mcp.db.mssql_python.connect",
        side_effect=mssql_python.Error("boom", "boom"),
    ):
        with pytest.raises(ConnectionError):
            connect("myserver", "mydb", MagicMock())


def test_connect_with_username_and_password_uses_sql_auth():
    with patch("sql_server_mcp.db.mssql_python.connect") as mock_connect:
        connect("myserver", "mydb", username="u", password="p;}w")

        args, kwargs = mock_connect.call_args
        assert "UID={u};" in args[0]
        assert "PWD={p;}}w};" in args[0]
        assert "token_provider" not in kwargs
