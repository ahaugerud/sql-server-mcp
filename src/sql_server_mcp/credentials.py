"""Local, single-user AAD credential acquisition."""

from __future__ import annotations

import sys
from typing import Any

from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential, InteractiveBrowserCredential

from sql_server_mcp.db import SQL_SERVER_SCOPE


class _LazyCredential(TokenCredential):
    """Defers the az-cli-or-browser login decision to the first `get_token`
    call, instead of blocking at construction time. The MCP server must
    finish its stdio handshake well within the client's connect timeout
    (commonly 30s); resolving a slow interactive browser login eagerly
    at startup blows through that window before the server can even start
    listening."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._resolved: TokenCredential | None = None

    def get_token(self, *scopes: str, **kwargs: Any):
        if self._resolved is None:
            self._resolved = self._resolve()
        return self._resolved.get_token(*scopes, **kwargs)

    def _resolve(self) -> TokenCredential:
        cli_credential = AzureCliCredential(tenant_id=self._tenant_id)
        try:
            cli_credential.get_token(SQL_SERVER_SCOPE)
            return cli_credential
        except ClientAuthenticationError:
            sys.stderr.write(
                f"No active `az login` session for tenant {self._tenant_id!r} - "
                "falling back to an interactive browser login.\n"
            )

        browser_credential = InteractiveBrowserCredential(tenant_id=self._tenant_id)
        browser_credential.get_token(SQL_SERVER_SCOPE)  # fail fast, surface errors now
        return browser_credential


def build_credential(tenant_id: str) -> TokenCredential:
    """Return a credential for `tenant_id`. Resolution (az-cli, falling back
    to an interactive browser login) is deferred to the first token request
    so server startup isn't blocked on login."""
    return _LazyCredential(tenant_id)


def get_access_token(credential: TokenCredential) -> str:
    """Fetch a SQL-scoped access token from `credential`."""
    return credential.get_token(SQL_SERVER_SCOPE).token
