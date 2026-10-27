from datetime import datetime

import pyarrow.parquet as pq

from sql_server_mcp.export import write_csv, write_parquet


def test_write_parquet_roundtrip(tmp_path):
    rows = [
        {"id": 1, "name": "a", "ts": datetime(2026, 1, 1), "amt": None},
        {"id": 2, "name": "b", "ts": datetime(2026, 1, 2), "amt": 1.5},
    ]
    path = tmp_path / "out.parquet"

    write_parquet(rows, str(path))

    assert pq.read_table(str(path)).to_pylist() == rows


def test_write_csv_roundtrip(tmp_path):
    rows = [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]
    path = tmp_path / "out.csv"

    write_csv(rows, str(path))

    content = path.read_text()
    assert content.splitlines() == ["id,name", "1,a", "2,b"]


def test_write_csv_is_utf8_regardless_of_locale(tmp_path, monkeypatch):
    monkeypatch.setattr("locale.getpreferredencoding", lambda *a, **k: "cp1252")
    rows = [{"name": "Å☃"}]
    path = tmp_path / "out.csv"

    write_csv(rows, str(path))

    assert path.read_bytes().decode("utf-8").splitlines()[1] == "Å☃"
