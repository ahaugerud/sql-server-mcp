"""Writing query results to a local Parquet or CSV file."""

from __future__ import annotations

import csv
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet(rows: list[dict[str, Any]], path: str) -> None:
    pq.write_table(pa.Table.from_pylist(rows), path)


def write_csv(rows: list[dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
