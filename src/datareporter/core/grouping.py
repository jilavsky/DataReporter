"""Scope grouping and output-path resolution.

A *scope* decides how many datasets go into one output document:

========== =====================================================
``dataset``   one document per data file (many small files)
``technique`` one per technique folder (``Sample_usaxs`` ...)
``sample``    one per sample (all techniques combined)
``user``      one per user folder
========== =====================================================

An *output mode* decides where documents land (orthogonal to scope):

========== =====================================================
``source``  inside the input tree, next to the data it describes
``mirror``  under the output dir, reproducing the tree structure
``flat``    directly in the output dir, path baked into the name
========== =====================================================
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

from datareporter.core.model import Dataset, TECHNIQUES

__all__ = ["Scope", "OutputMode", "Group", "group_datasets", "resolve_output_dir"]

Scope = Literal["dataset", "technique", "sample", "user"]
OutputMode = Literal["source", "mirror", "flat"]

#: Display/order priority of techniques inside multi-technique documents.
_TECH_ORDER = {t: i for i, t in enumerate(("usaxs", "saxs", "waxs", "usaxs_merged"))}

_COLLECTION_RE = re.compile(r"_(\d+)(?:_merged)?$", re.IGNORECASE)


def _collection_num(name: str) -> int:
    """Return the collection number embedded in a dataset stem, or 0 if absent.

    Handles both plain files (``sample_0042``) and merged files
    (``sample_0042_merged``) by matching the last ``_<digits>`` before an
    optional ``_merged`` suffix.
    """
    m = _COLLECTION_RE.search(name)
    return int(m.group(1)) if m else 0


@dataclass
class Group:
    """A set of datasets that end up in one output document."""

    key: str                 #: unique key, path-like (relative to scan root)
    title: str               #: human-readable document title
    rel_dir: Path            #: group folder, relative to scan root
    stem: str                #: base filename for the document
    datasets: list[Dataset] = field(default_factory=list)

    @property
    def flat_stem(self) -> str:
        """Filename stem that encodes the full path (for flat output mode)."""
        return safe_name("_".join([*self.rel_dir.parts]) or self.stem)


def safe_name(name: str) -> str:
    """Sanitize a string for use as a filename (ASCII-safe)."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return name.strip("_") or "report"


def group_datasets(datasets: Iterable[Dataset], scope: Scope) -> list[Group]:
    """Group datasets according to *scope*.

    Group folders are derived from each file's real location, so this
    works for any scan-root depth.  Datasets inside each group are sorted
    by technique (usaxs, saxs, waxs, usaxs_merged) and then by name.
    """
    groups: dict[str, Group] = {}
    for d in datasets:
        rel_parent = d.rel_path.parent  # technique folder (or containing folder)
        if scope == "dataset":
            rel_dir, stem = rel_parent, d.name
            key = str(rel_parent / d.name)
            title = d.name
        elif scope == "technique":
            rel_dir, stem = rel_parent, rel_parent.name or d.name
            key = str(rel_parent)
            title = rel_parent.name or d.name
        elif scope == "sample":
            sample_dir = rel_parent.parent if d.technique else rel_parent
            rel_dir = sample_dir
            stem = sample_dir.name or d.sample or d.name
            key = str(sample_dir)
            title = stem
        elif scope == "user":
            sample_dir = rel_parent.parent if d.technique else rel_parent
            user_dir = sample_dir.parent
            rel_dir = user_dir
            stem = user_dir.name or d.user or "user"
            key = str(user_dir)
            title = stem
        else:  # pragma: no cover - guarded by Literal type
            raise ValueError(f"Unknown scope: {scope}")

        grp = groups.get(key)
        if grp is None:
            grp = groups[key] = Group(key=key, title=title, rel_dir=rel_dir, stem=safe_name(stem))
        grp.datasets.append(d)

    for grp in groups.values():
        grp.datasets.sort(key=lambda d: (_TECH_ORDER.get(d.technique, 99), _collection_num(d.name), d.name))
    return sorted(groups.values(), key=lambda g: g.key)


def resolve_output_dir(
    group: Group,
    mode: OutputMode,
    output_dir: Path | None,
    input_root: Path,
) -> tuple[Path, str]:
    """Return ``(directory, filename_stem)`` for a group's document.

    * ``source`` — ``<input_root>/<group.rel_dir>/<stem>.<ext>``
    * ``mirror`` — ``<output_dir>/<group.rel_dir>/<stem>.<ext>``
    * ``flat``   — ``<output_dir>/<flat_stem>.<ext>``

    Raises ``ValueError`` when a required directory is missing.
    """
    if mode == "source":
        return input_root / group.rel_dir, group.stem
    if output_dir is None:
        raise ValueError(f"Output mode '{mode}' requires an output directory")
    if mode == "mirror":
        return Path(output_dir) / group.rel_dir, group.stem
    if mode == "flat":
        return Path(output_dir), group.flat_stem
    raise ValueError(f"Unknown output mode: {mode}")  # pragma: no cover
