"""Scans folders for Nexus HDF5 files and extracts metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class NexusRecord:
    path: Path
    filename: str
    size_bytes: int
    month: str = ""
    user: str = ""
    sample: str = ""
    technique: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    data_arrays: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


_HDF_EXTENSIONS = {".h5", ".hdf5", ".nxs", ".hdf"}


def scan_folders(folders: List[str | Path]) -> List[NexusRecord]:
    """Scan folder hierarchy for Nexus HDF5 files.

    Expected layout::

        <root>/YYYY_MM/<nn_nn_UserName>/<sampleName>/<technique>/*.hdf
    """
    records: List[NexusRecord] = []
    for folder in folders:
        root = Path(folder)
        if not root.is_dir():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                fpath = Path(dirpath) / fname
                if fpath.suffix.lower() in _HDF_EXTENSIONS:
                    records.append(_index_file(fpath, root))
    return records


def _index_file(path: Path, data_root: Path) -> NexusRecord:
    rel = path.relative_to(data_root)
    parts = rel.parts
    month = parts[0] if len(parts) > 0 else ""
    user = parts[1] if len(parts) > 1 else ""
    sample = parts[2] if len(parts) > 2 else ""
    technique = parts[3] if len(parts) > 3 else ""

    record = NexusRecord(
        path=path,
        filename=path.name,
        size_bytes=path.stat().st_size,
        month=month,
        user=user,
        sample=sample,
        technique=technique,
    )
    try:
        import h5py
        from datareporter.core.nexus_reader import read_metadata, read_sasdata
        with h5py.File(str(path), "r") as h5:
            _extract_metadata(h5, record)
            record.data_arrays = read_sasdata(h5)
    except Exception as exc:
        record.errors.append(str(exc))
    return record


def _extract_metadata(h5: "h5py.File", record: NexusRecord) -> None:
    try:
        meta = h5.get("entry/Metadata")
        if meta is None:
            return
        for key in meta:
            try:
                raw = meta[key][()]
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                elif hasattr(raw, "item"):
                    raw = raw.item()
                record.metadata[key] = raw
            except Exception:
                record.metadata[key] = None
    except Exception:
        pass
