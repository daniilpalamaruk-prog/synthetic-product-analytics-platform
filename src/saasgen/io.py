from __future__ import annotations

import csv
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


class DatasetWriter:
    """Append-only partition writer; each call is an independent Parquet part."""

    def __init__(self, root: Path, csv_sample: bool = False):
        self.root = root
        self.csv_sample = csv_sample
        self.parts: dict[tuple[str, str], int] = {}
        self.rows: dict[tuple[str, str], int] = {}

    def write(self, layer: str, table: str, records: list[dict]) -> None:
        if not records:
            return
        key = (layer, table)
        part = self.parts.get(key, 0)
        target = self.root / layer / table
        target.mkdir(parents=True, exist_ok=True)
        normalized = [_normalize(r) for r in records]
        pq.write_table(pa.Table.from_pylist(normalized), target / f"part-{part:05d}.parquet", compression="zstd")
        if self.csv_sample and part == 0:
            sample_dir = self.root / "sample"
            sample_dir.mkdir(parents=True, exist_ok=True)
            with (sample_dir / f"{table}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(normalized[0]))
                writer.writeheader()
                writer.writerows(normalized[: min(1000, len(normalized))])
        self.parts[key] = part + 1
        self.rows[key] = self.rows.get(key, 0) + len(records)


def _normalize(record: dict) -> dict:
    out = {}
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            out[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            out[key] = value
    return out


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")

