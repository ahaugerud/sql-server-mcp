"""Server-level tests using an in-memory FastMCP Client, with
sql_server_mcp.server.db.connect monkeypatched to a fake connection."""

from __future__ import annotations

import pytest

from sql_server_mcp.config import Settings
from sql_server_mcp.server import create_app


class FakeCursor:
    def __init__(self, canned_rows_by_sql_fragment):
        self._canned = canned_rows_by_sql_fragment
        self.description = []
        self._rows = []
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        for fragment, (columns, rows) in self._canned.items():
            if fragment in sql:
                self.description = [(c,) for c in columns]
                self._rows = rows
                return
        self.description = []
        self._rows = []

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class FakeConnection:
    def __init__(self, canned_rows_by_sql_fragment):
        self._cursor = FakeCursor(canned_rows_by_sql_fragment)

    def cursor(self):
        return self._cursor

    def close(self):
        pass


class FakeAccessToken:
    def __init__(self, token):
        self.token = token


class FakeCredential:
    """Stands in for a real azure-identity TokenCredential in tests."""

    def get_token(self, *scopes, **kwargs):
        return FakeAccessToken("fake-token")


@pytest.fixture
def settings():
    return Settings(
        sql_server_name="myserver",
        sql_database_name="mydb",
        tenant_id="11111111-1111-1111-1111-111111111111",
        max_rows=5,
    )


@pytest.fixture
def credential():
    return FakeCredential()


def _install_fake_db(monkeypatch, canned_rows_by_sql_fragment):
    connection = FakeConnection(canned_rows_by_sql_fragment)
    monkeypatch.setattr(
        "sql_server_mcp.server.db.connect",
        lambda *args, **kwargs: connection,
    )
    return connection


@pytest.mark.asyncio
async def test_query_tool_executes_readonly_select(settings, credential, monkeypatch):
    connection = _install_fake_db(
        monkeypatch,
        {"AS smoke_test": (["smoke_test"], [(1,)])},
    )
    app = create_app(settings, credential)

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool("query", {"sql": "SELECT 1 AS smoke_test"})

    assert "smoke_test" in result.data
    assert "1" in result.data
    executed_sql = connection.cursor().executed[0][0]
    assert "TOP 5" in executed_sql  # settings.max_rows applied


@pytest.mark.asyncio
async def test_query_tool_rejects_non_select(settings, credential, monkeypatch):
    _install_fake_db(monkeypatch, {})
    app = create_app(settings, credential)

    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    async with Client(app) as client:
        with pytest.raises(ToolError):
            await client.call_tool("query", {"sql": "DROP TABLE foo"})


@pytest.mark.asyncio
async def test_query_tool_rejects_multiple_statements(settings, credential, monkeypatch):
    _install_fake_db(monkeypatch, {})
    app = create_app(settings, credential)

    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    async with Client(app) as client:
        with pytest.raises(ToolError):
            await client.call_tool("query", {"sql": "SELECT 1; SELECT 2;"})


@pytest.mark.asyncio
async def test_list_databases_tool(settings, credential, monkeypatch):
    _install_fake_db(
        monkeypatch,
        {"sys.databases": (["database_name"], [("Sales",), ("Staging",)])},
    )
    app = create_app(settings, credential)

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool("list_databases", {})

    assert "Sales" in result.data
    assert "Staging" in result.data


@pytest.mark.asyncio
async def test_search_schema_uses_provided_databases_without_listing(
    settings, credential, monkeypatch
):
    connection = _install_fake_db(
        monkeypatch,
        {
            "INFORMATION_SCHEMA.TABLES": (
                ["DatabaseName", "TABLE_NAME"],
                [("Sales", "Customers")],
            )
        },
    )
    app = create_app(settings, credential)

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool(
            "search_schema",
            {"target": "tables", "name": "customer", "databases": ["Sales"]},
        )

    assert "Customers" in result.data
    # Only one query should have run - the schema search itself - since an
    # explicit `databases` list was given and list_databases shouldn't be
    # called to discover it.
    assert len(connection.cursor().executed) == 1


@pytest.mark.asyncio
async def test_search_schema_discovers_databases_when_not_provided(
    settings, credential, monkeypatch
):
    connection = _install_fake_db(
        monkeypatch,
        {
            "sys.databases": (["database_name"], [("Sales",)]),
            "INFORMATION_SCHEMA.TABLES": (
                ["DatabaseName", "TABLE_NAME"],
                [("Sales", "Customers")],
            ),
        },
    )
    app = create_app(settings, credential)

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool(
            "search_schema", {"target": "tables", "name": "customer"}
        )

    assert "Customers" in result.data
    assert len(connection.cursor().executed) == 2


@pytest.mark.asyncio
async def test_export_query_writes_file_uncapped(settings, credential, monkeypatch, tmp_path):
    rows = [(i, f"name{i}") for i in range(30)]  # more than settings.max_rows (5)
    _install_fake_db(monkeypatch, {"AS smoke_test": (["id", "name"], rows)})
    app = create_app(settings, credential)
    path = tmp_path / "out.parquet"

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool(
            "export_query",
            {"sql": "SELECT id, name AS smoke_test FROM foo", "path": str(path)},
        )

    assert "30 rows" in result.data
    assert path.exists()


@pytest.mark.asyncio
async def test_export_query_rejects_non_select(settings, credential, monkeypatch, tmp_path):
    _install_fake_db(monkeypatch, {})
    app = create_app(settings, credential)

    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    async with Client(app) as client:
        with pytest.raises(ToolError):
            await client.call_tool(
                "export_query",
                {"sql": "DROP TABLE foo", "path": str(tmp_path / "out.parquet")},
            )


@pytest.mark.asyncio
async def test_export_query_no_rows_writes_no_file(settings, credential, monkeypatch, tmp_path):
    _install_fake_db(monkeypatch, {})
    app = create_app(settings, credential)
    path = tmp_path / "out.parquet"

    from fastmcp import Client

    async with Client(app) as client:
        result = await client.call_tool(
            "export_query", {"sql": "SELECT 1 AS x", "path": str(path)}
        )

    assert "0 rows" in result.data
    assert not path.exists()
