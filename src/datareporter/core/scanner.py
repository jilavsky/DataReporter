"""Fast folder-tree scanner.

Walks the instrument data tree and indexes HDF5 files **without opening
them** — classification relies purely on folder names, so scanning a
month with thousands of files takes well under a second.  HDF5 content
is read later inside rendering workers (:mod:`datareporter.core.nexus`).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, Iterable, Optional

from datareporter.core.model import Dataset, HDF_EXTENSIONS, technique_from_folder

__all__ = ["scan", "filter_datasets"]


def scan(root: str | Path) -> list[Dataset]:
    """Index all HDF5 files under *root*.

    The root may point at any level of the hierarchy (year, month, user,
    sample, or a single technique folder); classification is anchored on
    the technique folder (``*_usaxs`` etc.) rather than on depth from the
    root, so partial trees work naturally.

    Returns datasets sorted by path (stable order for grouping and
    reproducible reports).
    """
    root = Path(root).resolve()
    datasets: list[Dataset] = []
    if not root.is_dir():
        return datasets

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden folders and previously generated Attachments folders.
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "Attachments"]
        folder = Path(dirpath)
        for fname in filenames:
            if Path(fname).suffix.lower() not in HDF_EXTENSIONS:
                continue
            datasets.append(_classify(folder / fname, root))

    datasets.sort(key=lambda d: str(d.path))
    return datasets


def _classify(path: Path, root: Path) -> Dataset:
    """Build a :class:`Dataset` for *path*, inferring hierarchy fields.

    Anchors on the technique folder: the file's parent folder is expected
    to be ``<Sample>_<technique>``; the sample, user, and month names are
    the successive parents above it.  When the parent folder does not
    follow the technique convention, technique stays ``""`` and the
    parent is recorded as the sample.
    """
    parent = path.parent
    technique = technique_from_folder(parent.name)

    if technique:
        sample_dir = parent.parent
        sample = sample_dir.name if sample_dir != sample_dir.parent else ""
        user_dir = sample_dir.parent
        user = user_dir.name if user_dir != user_dir.parent else ""
        month = user_dir.parent.name if user_dir.parent != user_dir.parent.parent else ""
    else:
        sample = parent.name
        user = parent.parent.name if parent.parent != parent.parent.parent else ""
        month = ""

    try:
        size = path.stat().st_size
    except OSError:
        size = 0

    return Dataset(
        path=path,
        root=root,
        month=month,
        user=user,
        sample=sample,
        technique=technique,
        size_bytes=size,
    )


def filter_datasets(
    datasets: Iterable[Dataset],
    select: Optional[str] = None,
    blanks: str = "include",
    predicate: Optional[Callable[[Dataset], bool]] = None,
) -> list[Dataset]:
    """Filter datasets by regex, blank handling, and/or custom predicate.

    Args:
        datasets: Datasets to filter.
        select: Regular expression matched (``re.search``, case-insensitive)
            against the path relative to the scan root.  ``None`` keeps all.
        blanks: ``"include"`` (default), ``"exclude"`` (drop files whose
            name contains "blank"), or ``"only"`` (keep only blanks).
        predicate: Optional callable for arbitrary additional filtering.

    Raises:
        re.error: If *select* is not a valid regular expression.
    """
    pattern = re.compile(select, re.IGNORECASE) if select else None
    out: list[Dataset] = []
    for d in datasets:
        if pattern and not pattern.search(str(d.rel_path)):
            continue
        if blanks == "exclude" and d.is_blank():
            continue
        if blanks == "only" and not d.is_blank():
            continue
        if predicate and not predicate(d):
            continue
        out.append(d)
    return out
