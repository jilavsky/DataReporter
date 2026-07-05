"""Scans folders for Nexus HDF5 files and extracts metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class NexusRecord:
    path: Path
    filename: str
    size_bytes: int
    entries: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def scan_folders(folders: List[str | Path]) -> List[NexusRecord]:
    """Return Nexus records for every HDF5 file found under *folders*."""
    records: List[NexusRecord] = []
    for folder in folders:
        root = Path(folder)
        if not root.is_dir():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = Path(dirpath) / fname
                if fpath.suffix.lower() in {".h5", ".hdf5", ".nxs"}:
                    records.append(_index_file(fpath))
    return records


def _index_file(path: Path) -> NexusRecord:
    record = NexusRecord(path=path, filename=path.name, size_bytes=path.stat().st_size)
    try:
        import h5py
        with h5py.File(path, "r") as h5:
            _walk(h5, "/", record, max_depth=3)
    except Exception as exc:
        record.errors.append(str(exc))
    return record


def _walk(group, prefix: str, record: NexusRecord, max_depth: int) -> None:
    if max_depth <= 0:
        return
    for key in group:
        name = f"{prefix}/{key}"
        try:
            item = group[key]
        except Exception:
            record.entries.append(name)
            continue
        if hasattr(item, "keys"):
            _walk(item, name, record, max_depth - 1)
        else:
            record.entries.append(name)
