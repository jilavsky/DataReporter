"""All HDF5 (NXcanSAS) access lives in this module.

Two public functions:

* :func:`read_curve` — return the reduced 1-D curve (Q, I, Idev) of a file.
* :func:`read_metadata` — return a small dict of high-level metadata.

Both are designed to be called inside worker processes; they open the
file, read what they need, and close it again.

Extending metadata
------------------
:data:`METADATA_KEYS` maps a display label to a list of candidate HDF5
paths tried in order (first hit wins).  Paths starting with ``@entry``
are resolved from the file root; paths starting with ``@sasentry`` are
resolved relative to the SASentry subentry that holds the plotted data.
To surface a new metadata item in reports, add one line here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import h5py
import numpy as np

__all__ = ["Curve", "read_curve", "read_metadata", "METADATA_KEYS"]


#: label -> candidate HDF5 paths (first existing one wins).
#: ``@sasentry/...`` = relative to the SASentry containing the plotted data;
#: ``@entry/...``   = relative to the file root.
METADATA_KEYS: dict[str, list[str]] = {
    "Title": ["@sasentry/title", "@entry/entry/title"],
    "Sample name": ["@sasentry/sassample/name"],
    "Thickness (mm)": ["@sasentry/sassample/thickness"],
    "Transmission": ["@sasentry/sastransmission_spectrum/T"],
    "SDD (mm)": ["@sasentry/sasinstrument/sasdetector/SDD"],
    "Wavelength (A)": ["@sasentry/sasinstrument/sassource/wavelength"],
    "Start time": [
        "@entry/entry/Metadata/StartTime",
        "@entry/entry/metadata/StartTime",
        "@entry/entry/start_time",
    ],
}


@dataclass
class Curve:
    """Reduced 1-D scattering curve."""

    q: np.ndarray
    i: np.ndarray
    idev: Optional[np.ndarray] = None
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def read_curve(path: str | Path, with_metadata: bool = True) -> Curve:
    """Read the primary reduced curve from an NXcanSAS file.

    USAXS files contain both a desmeared and a slit-smeared (``*_SMR``)
    SASentry; the desmeared one is preferred.  Files without any SASdata
    group (e.g. blank measurements) fall back to the raw ``entry/QRS_data``
    or ``entry/Blank_data`` arrays.  Raises ``ValueError`` when no usable
    data is found at all.
    """
    path = Path(path)
    with h5py.File(str(path), "r") as h5:
        sasdata_path = _pick_sasdata(h5)
        if sasdata_path is not None:
            grp = h5[sasdata_path]
            q = _read_array(grp, "Q")
            i = _read_array(grp, "I")
            if q is None or i is None:
                raise ValueError(f"SASdata group {sasdata_path} lacks Q/I arrays in {path.name}")
            idev = _read_array(grp, "Idev")
            meta = _read_metadata_from(h5, sasdata_path) if with_metadata else {}
            return Curve(q=q, i=i, idev=idev, label=path.stem, metadata=meta)

        # Fallback for files without reduced SASdata (e.g. blanks).
        for grp_name in ("entry/QRS_data", "entry/Blank_data"):
            grp = h5.get(grp_name)
            if grp is None:
                continue
            q = _read_array(grp, "Q")
            i = _read_array(grp, "Intensity")
            if q is not None and i is not None:
                idev = _read_array(grp, "Error")
                meta = _read_metadata_from(h5, None) if with_metadata else {}
                return Curve(q=q, i=i, idev=idev, label=path.stem, metadata=meta)

        raise ValueError(f"No NXcanSAS SASdata (or raw QRS/Blank) data found in {path.name}")


def read_metadata(path: str | Path) -> dict[str, Any]:
    """Read high-level metadata (see :data:`METADATA_KEYS`) from a file."""
    with h5py.File(str(path), "r") as h5:
        sasdata_path = _pick_sasdata(h5)
        return _read_metadata_from(h5, sasdata_path)


# ── internals ─────────────────────────────────────────────────────────────

def _pick_sasdata(h5: h5py.File) -> Optional[str]:
    """Locate the preferred SASdata group.

    Finds all groups with attribute ``canSAS_class == "SASdata"`` and
    prefers one whose parent SASentry is not slit-smeared (``*_SMR``).
    """
    matches: list[str] = []

    def _visit(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group) and _attr(obj, "canSAS_class") == "SASdata":
            matches.append(name)

    h5.visititems(_visit)
    if not matches:
        return None
    for m in matches:
        parent = m.rsplit("/", 1)[0] if "/" in m else ""
        if not parent.upper().endswith("_SMR"):
            return m
    return matches[0]


def _attr(obj: Any, key: str) -> str:
    val = obj.attrs.get(key)
    if isinstance(val, bytes):
        return val.decode("utf-8", "replace")
    return str(val) if val is not None else ""


def _read_array(grp: h5py.Group, key: str) -> Optional[np.ndarray]:
    ds = grp.get(key)
    if ds is None:
        return None
    try:
        arr = np.asarray(ds[()], dtype=float).ravel()
    except (TypeError, ValueError):
        return None
    return arr if arr.size > 1 else None


def _read_metadata_from(h5: h5py.File, sasdata_path: Optional[str]) -> dict[str, Any]:
    sasentry = sasdata_path.rsplit("/", 1)[0] if sasdata_path and "/" in sasdata_path else ""
    out: dict[str, Any] = {}
    for label, candidates in METADATA_KEYS.items():
        for cand in candidates:
            if cand.startswith("@sasentry/"):
                if not sasentry:
                    continue
                hpath = f"{sasentry}/{cand[len('@sasentry/'):]}"
            elif cand.startswith("@entry/"):
                hpath = cand[len("@entry/"):]
            else:
                hpath = cand
            val = _read_scalar(h5, hpath)
            if val is not None:
                out[label] = val
                break
    return out


def _read_scalar(h5: h5py.File, hpath: str) -> Optional[Any]:
    try:
        ds = h5.get(hpath)
        if ds is None or not isinstance(ds, h5py.Dataset):
            return None
        val = ds[()]
    except (KeyError, OSError, TypeError):
        return None
    if isinstance(val, bytes):
        return val.decode("utf-8", "replace")
    if isinstance(val, np.ndarray):
        if val.size != 1:
            return None
        val = val.reshape(-1)[0]
        if isinstance(val, bytes):
            return val.decode("utf-8", "replace")
    if hasattr(val, "item"):
        val = val.item()
        if isinstance(val, bytes):
            return val.decode("utf-8", "replace")
    if isinstance(val, float):
        return round(val, 6)
    return val
