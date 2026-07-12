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
    parents: list[str] = []
    p = path.parent
    while p != data_root and p != p.parent:
        parents.append(p.name)
        p = p.parent
    # Do NOT include data_root itself; work only with folders below the selected root.
    parents.reverse()
    # Deepest folder below root -> technique, then sample, user, month.
    technique = parents[-1] if len(parents) > 0 else ""
    sample = parents[-2] if len(parents) > 1 else ""
    user = parents[-3] if len(parents) > 2 else ""
    month = parents[-4] if len(parents) > 3 else ""

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


def list_directory(path: Path) -> List[dict]:
    """Fast shallow listing of a directory.

    Returns a list of dicts with keys: name, type ('folder'|'file'), size_bytes.
    Only immediate children are returned; no HDF5 metadata is read and no recursion.
    For folders, only the direct child files' sizes are counted (not recursive).
    """
    results: List[dict] = []
    if not path.is_dir():
        return results
    for entry in sorted(path.iterdir()):
        try:
            stat = entry.stat()
        except OSError:
            continue
        if entry.is_file() and entry.suffix.lower() in _HDF_EXTENSIONS:
            results.append({"name": entry.name, "type": "file", "size_bytes": stat.st_size})
        elif entry.is_dir():
            # Only count direct HDF5 children (no recursion) — fast!
            total_size = 0
            file_count = 0
            try:
                for sub in entry.iterdir():
                    if sub.is_file() and sub.suffix.lower() in _HDF_EXTENSIONS:
                        file_count += 1
                        try:
                            total_size += sub.stat().st_size
                        except OSError:
                            pass
            except OSError:
                pass
            results.append({
                "name": entry.name,
                "type": "folder",
                "size_bytes": total_size,
                "_file_count": file_count,
            })
    return results


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
