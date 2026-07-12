"""Tests for NXcanSAS reading (curves, SMR preference, metadata)."""

from __future__ import annotations

import numpy as np
import pytest

from datareporter.core.nexus import read_curve, read_metadata
from tests.conftest import make_nxcansas_file


def test_read_curve(tmp_path):
    f = make_nxcansas_file(tmp_path / "a.h5", n=40, title="hello")
    c = read_curve(f)
    assert c.q.shape == (40,)
    assert c.i.shape == (40,)
    assert c.idev is not None
    assert c.label == "a"


def test_smr_entry_is_skipped(tmp_path):
    f = make_nxcansas_file(tmp_path / "b.h5", with_smr=True)
    import h5py

    # corrupt the SMR entry's data so picking it would fail loudly
    with h5py.File(str(f), "r+") as h5:
        del h5["entry/b_SMR/sasdata/I"]
    c = read_curve(f)  # must succeed via the desmeared entry
    assert np.all(np.isfinite(c.i))


def test_metadata_extraction(tmp_path):
    f = make_nxcansas_file(tmp_path / "c.h5", title="my title")
    meta = read_metadata(f)
    assert meta.get("Title") == "my title"
    assert meta.get("Sample name") == "my title"
    assert meta.get("Thickness (mm)") == pytest.approx(1.2)


def test_file_without_sasdata_raises(tmp_path):
    import h5py

    f = tmp_path / "empty.h5"
    with h5py.File(str(f), "w") as h5:
        h5.create_dataset("entry/data", data=np.arange(5))
    with pytest.raises(ValueError):
        read_curve(f)


def test_blank_data_fallback(tmp_path):
    import h5py

    f = tmp_path / "blank.h5"
    with h5py.File(str(f), "w") as h5:
        g = h5.create_group("entry/Blank_data")
        g.create_dataset("Q", data=np.geomspace(1e-4, 1, 30))
        g.create_dataset("Intensity", data=np.ones(30))
        g.create_dataset("Error", data=np.ones(30) * 0.1)
    c = read_curve(f)
    assert c.q.shape == (30,)
