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


def read_metadata(h5: h5py.File) -> dict[str, Any]:
    """Return entry/Metadata as a flat dict of scalar values."""
    out: dict[str, Any] = {}
    try:
        meta = h5.get("entry/Metadata")
        if meta is None:
            return out
        for key in meta:
            try:
                val = meta[key][()]
                if hasattr(val, "item"):
                    val = val.item()
                out[key] = val
            except Exception:
                out[key] = None
    except Exception:
        pass
    return out


def read_sasdata(h5: h5py.File) -> dict[str, Any]:
    """Return sasdata arrays as a dict."""
    out: dict[str, Any] = {}
    for key in ["Q", "I", "Idev", "Qdev"]:
        p = f"entry/sasdata/{key}"
        try:
            ds = h5.get(p)
            if ds is not None:
                out[key] = ds[()]
        except Exception:
            pass
    return out
