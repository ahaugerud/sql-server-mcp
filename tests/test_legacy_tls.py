import os

from sql_server_mcp.legacy_tls import enable_legacy_tls


def test_enable_legacy_tls_sets_openssl_conf(monkeypatch):
    monkeypatch.delenv("OPENSSL_CONF", raising=False)

    enable_legacy_tls()

    path = os.environ["OPENSSL_CONF"]
    try:
        with open(path) as f:
            assert "@SECLEVEL=0" in f.read()
    finally:
        os.remove(path)
        monkeypatch.delenv("OPENSSL_CONF", raising=False)
