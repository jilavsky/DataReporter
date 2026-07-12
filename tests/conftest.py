"""Shared pytest fixtures.

``sample_tree`` builds a small synthetic data tree following the real
instrument layout, with valid NXcanSAS HDF5 files, so all tests run
without the (large) real data present.
"""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
#: Real example data checked into the repo (used by the smoke test).
DATA_DIR = REPO_ROOT / "data"


def make_nxcansas_file(
    path: Path,
    n: int = 50,
    with_smr: bool = False,
    title: str = "test sample",
) -> Path:
    """Write a minimal valid NXcanSAS file with Q/I/Idev arrays."""
    path.parent.mkdir(parents=True, exist_ok=True)
    q = np.geomspace(1e-4, 1.0, n)
    i = q ** -3.5 + 0.1
    with h5py.File(str(path), "w") as h5:
        def add_entry(name: str) -> None:
            entry = h5.create_group(f"entry/{name}")
            entry.attrs["NX_class"] = "NXsubentry"
            entry.attrs["canSAS_class"] = "SASentry"
            entry.create_dataset("title", data=title.encode())
            sas = entry.create_group("sasdata")
            sas.attrs["NX_class"] = "NXdata"
            sas.attrs["canSAS_class"] = "SASdata"
            sas.create_dataset("Q", data=q)
            sas.create_dataset("I", data=i)
            sas.create_dataset("Idev", data=i * 0.02)
            sample = entry.create_group("sassample")
            sample.attrs["canSAS_class"] = "SASsample"
            sample.create_dataset("name", data=title.encode())
            sample.create_dataset("thickness", data=1.2)

        root = h5["/"].create_group("entry") if "entry" not in h5 else h5["entry"]
        root.attrs["NX_class"] = "NXentry"
        add_entry(path.stem)
        if with_smr:
            add_entry(f"{path.stem}_SMR")
    return path


@pytest.fixture()
def sample_tree(tmp_path: Path) -> Path:
    """Synthetic ``<root>/<user>/<sample>/<sample>_<technique>/*.h5`` tree."""
    root = tmp_path / "2026-07"
    layout = {
        "07_01_UserA": {
            "S1": ["usaxs", "saxs", "waxs"],
            "S2": ["usaxs", "saxs"],
        },
        "07_09_UserB": {
            "S3": ["usaxs", "usaxs_merged"],
        },
    }
    for user, samples in layout.items():
        for sample, techniques in samples.items():
            for tech in techniques:
                folder = root / user / sample / f"{sample}_{tech}"
                for k in range(3):
                    make_nxcansas_file(
                        folder / f"{sample}_meas_{k:04d}.h5",
                        with_smr=(tech == "usaxs"),
                        title=f"{sample} run {k}",
                    )
                make_nxcansas_file(folder / f"Blank_{tech}_0000.h5")
    return root
