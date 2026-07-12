"""Data model for DataReporter.

A :class:`Dataset` describes one reduced-data HDF5 file found in the
instrument folder tree.  It carries only cheap filesystem-derived
information; HDF5 content (curves, metadata) is read later, inside
rendering workers (see :mod:`datareporter.core.nexus`).

Expected folder layout (the scan root may be any level of it)::

    <YYYY>/<YYYY-MM>/<MM_DD_UserName>/<SampleName>/<SampleName>_<technique>/*.h5

where ``technique`` is one of ``usaxs``, ``saxs``, ``waxs`` or
``usaxs_merged``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

#: File extensions treated as HDF5 data files.
HDF_EXTENSIONS = {".h5", ".hdf5", ".hdf", ".nxs"}

#: Known technique folder suffixes, longest first so ``usaxs_merged``
#: wins over ``usaxs``.
TECHNIQUES = ("usaxs_merged", "usaxs", "saxs", "waxs")


def technique_from_folder(folder_name: str) -> str:
    """Infer technique from a data folder name like ``Sample_usaxs``.

    Returns one of :data:`TECHNIQUES` or ``""`` when the folder does not
    follow the convention.
    """
    low = folder_name.lower()
    for tech in TECHNIQUES:
        if low.endswith("_" + tech) or low == tech:
            return tech
    return ""


@dataclass
class Dataset:
    """One reduced-data HDF5 file located in the instrument tree."""

    path: Path              #: absolute path to the HDF5 file
    root: Path              #: scan root the file was found under
    month: str = ""         #: e.g. ``2026-07`` ("" when root is deeper)
    user: str = ""          #: e.g. ``07_01_Servis``
    sample: str = ""        #: e.g. ``AHM_stepScan``
    technique: str = ""     #: usaxs | saxs | waxs | usaxs_merged
    size_bytes: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def rel_path(self) -> Path:
        """Path relative to the scan root."""
        try:
            return self.path.relative_to(self.root)
        except ValueError:
            return self.path

    @property
    def name(self) -> str:
        """File stem, used as the dataset display name."""
        return self.path.stem

    @property
    def uid(self) -> str:
        """Short, deterministic identifier derived from the relative path.

        Used for cache image filenames so images map back to datasets
        exactly (no filename guessing).
        """
        return hashlib.sha1(str(self.rel_path).encode("utf-8")).hexdigest()[:12]

    def is_blank(self) -> bool:
        """True when the file name suggests a blank/background measurement."""
        return "blank" in self.name.lower()
