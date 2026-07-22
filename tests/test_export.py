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
