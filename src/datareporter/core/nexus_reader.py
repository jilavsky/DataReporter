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
    """Return SAS data arrays from NXcanSAS SASdata groups.

    Uses attribute-based group discovery to locate the correct SASdata
    group(s) marked with ``@canSAS_class = "SASdata"``, matching the
    NXcanSAS specification and the extraction logic used by pyirena.
    """
    out: dict[str, Any] = {}
    paths = _find_sasdata_groups(h5)
    if not paths:
        return out

    sas = h5[paths[0]]
    for key in ["Q", "I", "Idev", "Qdev", "dQw", "dQl"]:
        p = f"{sas.name}/{key}" if sas.name != "/" else key
        try:
            ds = h5.get(p)
            if ds is not None:
                out[key] = ds[()]
        except Exception:
            pass
    return out


def _find_sasdata_groups(h5: "h5py.File") -> list[str]:
    """Find groups with attribute ``canSAS_class = SASdata``."""
    matches: list[str] = []

    def _check(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group):
            attr = obj.attrs.get("canSAS_class")
            if attr is not None:
                val = attr.decode("utf-8") if isinstance(attr, bytes) else str(attr)
                if val == "SASdata":
                    matches.append(name)

    try:
        h5.visititems(_check)
    except Exception:
        pass

    if matches:
        return matches

    paths: list[str] = []

    def _find(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group) and name.endswith("sasdata"):
            paths.append(name)

    try:
        h5.visititems(_find)
    except Exception:
        pass
    return paths
