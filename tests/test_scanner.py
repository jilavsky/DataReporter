"""Tests for the scanner module."""

from __future__ import annotations

from pathlib import Path

from datareporter.core.scanner import _index_file, scan_folders


def test_scan_folders_detects_hdf5(tmp_path: Path) -> None:
    (tmp_path / "a.h5").write_bytes(b"")
    (tmp_path / "b.txt").write_text("hello")
    records = scan_folders([str(tmp_path)])
    assert len(records) == 1
    assert records[0].filename == "a.h5"


def test_index_file_lists_entries(tmp_path: Path) -> None:
    import h5py
    import numpy as np

    path = tmp_path / "data.nxs"
    with h5py.File(str(path), "w") as h5:
        h5.create_dataset("/raw/signal", data=np.arange(5))
    record = _index_file(path)
    assert any("raw/signal" in e for e in record.entries)
