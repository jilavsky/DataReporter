"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest


@pytest.fixture()
def nexus_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.nxs"
    with h5py.File(str(path), "w") as h5:
        h5.create_dataset("/entry/data", data=np.arange(10))
        h5.create_group("/entry/meta")
    return path
