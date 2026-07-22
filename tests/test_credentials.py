"""
Tests for credentials.py, mocking the azure-identity credential classes so
these run without a real login.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ClientAuthenticationError

from sql_server_mcp.credentials import build_credential, get_access_token


def _fake_token(value="fake-token"):
    token = MagicMock()
    token.token = value
    return token


def test_build_credential_uses_azure_cli_when_it_works():
    with patch("sql_server_mcp.credentials.AzureCliCredential") as MockCli, patch(
        "sql_server_mcp.credentials.InteractiveBrowserCredential"
    ) as MockBrowser:
        MockCli.return_value.get_token.return_value = _fake_token()

        credential = build_credential("11111111-1111-1111-1111-111111111111")

        MockCli.assert_called_once_with(tenant_id="11111111-1111-1111-1111-111111111111")
        assert credential is MockCli.return_value
        MockBrowser.assert_not_called()


def test_build_credential_falls_back_to_browser_login():
    with patch("sql_server_mcp.credentials.AzureCliCredential") as MockCli, patch(
        "sql_server_mcp.credentials.InteractiveBrowserCredential"
    ) as MockBrowser:
        MockCli.return_value.get_token.side_effect = ClientAuthenticationError(
            "not logged in"
        )
        MockBrowser.return_value.get_token.return_value = _fake_token()

        credential = build_credential("tenant-123")

        MockBrowser.assert_called_once_with(tenant_id="tenant-123")
        assert credential is MockBrowser.return_value


def test_build_credential_propagates_browser_login_failure():
    with patch("sql_server_mcp.credentials.AzureCliCredential") as MockCli, patch(
        "sql_server_mcp.credentials.InteractiveBrowserCredential"
    ) as MockBrowser:
        MockCli.return_value.get_token.side_effect = ClientAuthenticationError("nope")
        MockBrowser.return_value.get_token.side_effect = ClientAuthenticationError(
            "browser login also failed"
        )

        with pytest.raises(ClientAuthenticationError):
            build_credential("tenant-123")


def test_get_access_token_returns_token_string():
    credential = MagicMock()
    credential.get_token.return_value = _fake_token("abc123")

    assert get_access_token(credential) == "abc123"
