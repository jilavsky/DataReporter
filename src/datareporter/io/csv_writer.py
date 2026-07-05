"""Write flat CSV reports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Sequence

from datareporter.core.scanner import NexusRecord


def write_csv(
    records: Sequence[NexusRecord],
    output_dir: Path,
    settings: dict,
) -> Path:
    delimiter = settings.get("csv_delimiter", ",")
    out_path = output_dir / f"report{'.tsv' if delimiter == chr(9) else '.csv'}"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow([
            "filename", "month", "user", "sample", "technique",
            "size_bytes", "start_time", "sample_title",
            "data_arrays", "errors",
        ])
        for r in records:
            writer.writerow([
                r.filename,
                r.month,
                r.user,
                r.sample,
                r.technique,
                r.size_bytes,
                _decode(r.metadata.get("StartTime")),
                _decode(r.metadata.get("SampleTitle")),
                ";".join(r.data_arrays.keys()),
                "; ".join(r.errors),
            ])
    return out_path


def _decode(val):
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:
            return str(val)
    return val
