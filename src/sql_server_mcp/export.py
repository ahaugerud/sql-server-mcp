"""Writing query results to a local Parquet, CSV or Excel file."""

from __future__ import annotations

import csv
from datetime import datetime, time
from typing import Any

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import pyarrow as pa
import pyarrow.parquet as pq


def write_parquet(rows: list[dict[str, Any]], path: str) -> None:
    pq.write_table(pa.Table.from_pylist(rows), path)


def write_csv(rows: list[dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


EXCEL_MAX_ROWS = 1_048_575  # sheet limit of 1,048,576 minus the header row


def _excel_value(value: Any) -> Any:
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub("", value)
    if isinstance(value, (datetime, time)) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def write_excel(rows: list[dict[str, Any]], path: str) -> None:
    if len(rows) > EXCEL_MAX_ROWS:
        raise ValueError(
            f"Result has {len(rows)} rows, which exceeds Excel's limit of "
            f"{EXCEL_MAX_ROWS}. Use format 'csv' or 'parquet' instead."
        )
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Results")
    ws.append(list(rows[0].keys()))
    for row in rows:
        ws.append([_excel_value(v) for v in row.values()])
    wb.save(path)
