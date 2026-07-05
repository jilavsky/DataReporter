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


def test_index_file_extracts_metadata(tmp_path: Path) -> None:
    import h5py
    import numpy as np

    path = tmp_path / "sample.nxs"
    with h5py.File(str(path), "w") as h5:
        h5.create_dataset("/entry/sasdata/Q", data=np.arange(5, dtype=float))
        h5.create_dataset("/entry/sasdata/I", data=np.arange(5, dtype=float))
        h5.create_dataset("entry/Metadata/SampleTitle", data=b"test")
    record = _index_file(path, tmp_path)
    assert record.metadata.get("SampleTitle") == "test"
    assert "Q" in record.data_arrays
    assert "I" in record.data_arrays
