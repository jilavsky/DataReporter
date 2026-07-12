"""Shared image cache to avoid regenerating graphs for multiple output formats."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional


def _record_hash(record: "NexusRecord") -> str:  # noqa: F821 forward ref
    """Deterministic hash for a record's data arrays — used as cache key."""
    h = hashlib.md5()
    for key in sorted(record.data_arrays.keys()):
        val = record.data_arrays[key]
        if hasattr(val, "tobytes"):
            h.update(key.encode())
            h.update(val.tobytes())
        elif isinstance(val, (list, tuple)):
            h.update(key.encode())
            for v in val:
                h.update(str(v).encode())
    return h.hexdigest()[:16]


def build_image_cache(
    records: List["NexusRecord"],  # noqa: F821 forward ref
    cache_dir: Path,
) -> Dict[str, str]:
    """Generate images for all records and return {record_hash: image_path} mapping.

    Uses file-based caching so repeated runs (e.g., PDF + MD) skip regeneration.
    Returns paths relative to cache_dir for portability.
    """
    from datareporter.io.image_writer import save_images as _save_images  # local import

    cache_dir.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, str] = {}

    # Check which records are already cached
    existing = set()
    if cache_dir.exists():
        for f in cache_dir.glob("*.jpg"):
            stem = f.stem  # e.g. "abc123def456_SampleName_technique_EPON826_0049.hdf"
            parts = stem.split("_", 1)
            if len(parts) == 2:
                existing.add(parts[0])

    uncached = []
    for r in records:
        rh = _record_hash(r)
        if rh not in existing:
            uncached.append((r, rh))

    if uncached:
        # Write uncached images to a temp dir, then move into cache
        tmp_dir = cache_dir / ".tmp"
        tmp_dir.mkdir(exist_ok=True)
        _save_images([r for r, _ in uncached], tmp_dir)

        # Map generated files back by matching filename patterns
        tmp_files = sorted(tmp_dir.glob("*.jpg"))
        for (record, rh), img_path in zip(uncached, tmp_files):
            dest = cache_dir / f"{rh}_{record.filename.replace(' ', '_')}.jpg"
            import shutil
            shutil.move(str(img_path), str(dest))
            mapping[rh] = str(dest)

        # Clean up temp dir
        import shutil as _shutil
        _shutil.rmtree(tmp_dir, ignore_errors=True)

    return mapping


def get_cached_image(
    record: "NexusRecord",  # noqa: F821 forward ref
    cache_dir: Path,
) -> Optional[Path]:
    """Look up a cached image for a single record."""
    rh = _record_hash(record)
    candidates = list(cache_dir.glob(f"{rh}_*.jpg"))
    if candidates:
        return candidates[0]
    return None
