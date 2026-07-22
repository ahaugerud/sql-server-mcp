"""Local, single-user AAD credential acquisition."""

from __future__ import annotations

import sys

from azure.core.credentials import TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import AzureCliCredential, InteractiveBrowserCredential

from sql_server_mcp.db import SQL_SERVER_SCOPE


def build_credential(tenant_id: str) -> TokenCredential:
    """Return a credential for `tenant_id`, falling back to an interactive
    browser login if there's no `az login` session for that tenant."""
    cli_credential = AzureCliCredential(tenant_id=tenant_id)
    try:
        cli_credential.get_token(SQL_SERVER_SCOPE)
        return cli_credential
    except ClientAuthenticationError:
        sys.stderr.write(
            f"No active `az login` session for tenant {tenant_id!r} - "
            "falling back to an interactive browser login.\n"
        )

    browser_credential = InteractiveBrowserCredential(tenant_id=tenant_id)
    browser_credential.get_token(SQL_SERVER_SCOPE)  # fail fast, surface errors now
    return browser_credential


def get_access_token(credential: TokenCredential) -> str:
    """Fetch a SQL-scoped access token from `credential`."""
    return credential.get_token(SQL_SERVER_SCOPE).token
