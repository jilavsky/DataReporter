"""Nexus-specific HDF5 reading helpers."""

from __future__ import annotations

from typing import Any

import h5py


def open_nexus(path: str | Path) -> h5py.File:
    """Open a Nexus HDF5 file."""
    return h5py.File(str(path), "r")


def list_entries(h5: h5py.File, path: str = "/") -> list[str]:
    """List direct entries under the given HDF5 group path."""
    try:
        return list(h5[path].keys())
    except Exception:
        return []


def read_dataset(h5: h5py.File, path: str) -> Any:
    """Read a dataset array from the HDF5 file."""
    try:
        return h5[path][()]
    except Exception as exc:
        return None
