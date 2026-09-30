"""Opt-in OpenSSL relaxation for old SQL Server hosts (e.g. SQL Server 2012).

The driver's OpenSSL 3 rejects the weak ciphers/certificates such hosts offer
at its default security level, so the server resets the connection during the
TLS handshake. Lowering the security level to 0 lets the handshake complete.
"""

from __future__ import annotations

import atexit
import os
import tempfile

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
    fd, path = tempfile.mkstemp(prefix="sql-server-mcp-openssl-", suffix=".cnf")
    with os.fdopen(fd, "w") as f:
        f.write(_OPENSSL_CONF)
    atexit.register(_remove, path)
    os.environ["OPENSSL_CONF"] = path


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
