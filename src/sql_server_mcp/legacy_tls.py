"""Opt-in OpenSSL relaxation for old SQL Server hosts (e.g. SQL Server 2012).

With OpenSSL 3's default security level the handshake with such hosts fails
and the server resets the connection (`TCP Provider: Error code 0x2746`).
Lowering the security level to 0 lets it complete. Only the security level
matters (allowing older TLS versions alone does not help), which suggests
weak parameters such as the server's certificate, but that is inferred, not
verified.

This must run before the driver loads: `OPENSSL_CONF` is inherited by child
processes and affects all TLS in this process, so it is only enabled on request.
"""

from __future__ import annotations

import os
import sys

_OPENSSL_CONF = """\
openssl_conf = default_conf
[default_conf]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
CipherString = DEFAULT:@SECLEVEL=0
"""


def enable_legacy_tls() -> None:
    """Point OPENSSL_CONF at a config with security level 0 (this process only)."""
    if os.environ.get("OPENSSL_CONF"):
        sys.stderr.write(
            "MCP_SQL_LEGACY_TLS: overriding existing OPENSSL_CONF="
            f"{os.environ['OPENSSL_CONF']}\n"
        )
    # Fixed per-user path (rewritten each start) so nothing accumulates when the
    # client kills the server without letting it clean up.
    cache_home = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    directory = os.path.join(cache_home, "sql-server-mcp")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "openssl-seclevel0.cnf")
    with open(path, "w") as f:
        f.write(_OPENSSL_CONF)
    os.environ["OPENSSL_CONF"] = path
