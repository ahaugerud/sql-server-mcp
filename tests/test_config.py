import pytest

from sql_server_mcp.config import ConfigError, load_settings


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    monkeypatch.setenv("MCP_SQL_SERVER_NAME", "myserver.fabric.microsoft.com")
    monkeypatch.setenv("MCP_SQL_DATABASE_NAME", "mydb")
    monkeypatch.setenv("MCP_AZURE_TENANT_ID", "11111111-1111-1111-1111-111111111111")


def test_load_settings_reads_required_and_optional_vars(monkeypatch):
    monkeypatch.setenv("MCP_MAX_ROWS", "10")

    settings = load_settings()

    assert settings.sql_server_name == "myserver.fabric.microsoft.com"
    assert settings.sql_database_name == "mydb"
    assert settings.tenant_id == "11111111-1111-1111-1111-111111111111"
    assert settings.max_rows == 10


def test_load_settings_defaults_max_rows_to_25(monkeypatch):
    monkeypatch.delenv("MCP_MAX_ROWS", raising=False)

    settings = load_settings()

    assert settings.max_rows == 25


@pytest.mark.parametrize(
    "missing_var",
    ["MCP_SQL_SERVER_NAME", "MCP_SQL_DATABASE_NAME", "MCP_AZURE_TENANT_ID"],
)
def test_load_settings_raises_on_missing_required_vars(monkeypatch, missing_var):
    monkeypatch.delenv(missing_var, raising=False)

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_rejects_non_integer_max_rows(monkeypatch):
    monkeypatch.setenv("MCP_MAX_ROWS", "not-a-number")

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_rejects_non_positive_max_rows(monkeypatch):
    monkeypatch.setenv("MCP_MAX_ROWS", "0")

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_sql_login_does_not_require_tenant(monkeypatch):
    monkeypatch.delenv("MCP_AZURE_TENANT_ID", raising=False)
    monkeypatch.setenv("MCP_SQL_USERNAME", "user")
    monkeypatch.setenv("MCP_SQL_PASSWORD", "pw")

    settings = load_settings()

    assert settings.uses_sql_login
    assert settings.username == "user"
    assert settings.password == "pw"


def test_load_settings_rejects_username_without_password(monkeypatch):
    monkeypatch.setenv("MCP_SQL_USERNAME", "user")
    monkeypatch.delenv("MCP_SQL_PASSWORD", raising=False)

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_trust_server_certificate(monkeypatch):
    assert load_settings().trust_server_certificate is False

    monkeypatch.setenv("MCP_SQL_TRUST_SERVER_CERTIFICATE", "true")
    assert load_settings().trust_server_certificate is True


def test_load_settings_rejects_invalid_trust_server_certificate(monkeypatch):
    monkeypatch.setenv("MCP_SQL_TRUST_SERVER_CERTIFICATE", "maybe")

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_legacy_tls(monkeypatch):
    assert load_settings().legacy_tls is False

    monkeypatch.setenv("MCP_SQL_USERNAME", "user")
    monkeypatch.setenv("MCP_SQL_PASSWORD", "pw")
    monkeypatch.setenv("MCP_SQL_LEGACY_TLS", "true")
    assert load_settings().legacy_tls is True


def test_load_settings_rejects_invalid_legacy_tls(monkeypatch):
    monkeypatch.setenv("MCP_SQL_LEGACY_TLS", "maybe")

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_legacy_tls_requires_sql_login(monkeypatch):
    monkeypatch.setenv("MCP_SQL_LEGACY_TLS", "true")

    with pytest.raises(ConfigError):
        load_settings()
