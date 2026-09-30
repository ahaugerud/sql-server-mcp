import os

from sql_server_mcp.legacy_tls import enable_legacy_tls


def test_enable_legacy_tls_sets_openssl_conf(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENSSL_CONF", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    enable_legacy_tls()

    path = os.environ["OPENSSL_CONF"]
    try:
        assert path.startswith(str(tmp_path))
        with open(path) as f:
            assert "@SECLEVEL=0" in f.read()
    finally:
        monkeypatch.delenv("OPENSSL_CONF", raising=False)
