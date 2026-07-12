"""ASCII data export: one ``.dat`` file per dataset.

Format: commented header (source file, sample, technique, high-level
metadata) followed by three whitespace-separated columns ``Q I Idev``.
This is the standard input format for most SAS analysis tools.

Unlike the other writers, exporting raw data requires reading the HDF5
files; the reads happen inside this module's own process pool.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Optional, Sequence

__all__ = ["export_ascii"]


def _export_one(args: tuple[str, str, str, str, str]) -> tuple[str, str]:
    """Worker: read one HDF5 file and write its .dat next to *out_path*.

    Returns ``(out_path, error)`` — error is "" on success.
    """
    fpath, out_path, sample, technique, rel = args
    import numpy as np

    from datareporter.core.nexus import read_curve

    try:
        c = read_curve(fpath)
        header_lines = [
            f"Source file: {rel}",
            f"Sample: {sample}",
            f"Technique: {technique}",
        ]
        header_lines += [f"{k}: {v}" for k, v in c.metadata.items()]
        header_lines.append("Columns: Q(1/A)  Intensity  Idev")
        idev = c.idev if c.idev is not None else np.zeros_like(c.i)
        data = np.column_stack([c.q, c.i, idev])
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(out_path, data, fmt="%.6e",
                   header="\n".join(header_lines), comments="# ")
        return out_path, ""
    except Exception as exc:  # noqa: BLE001 — collect, don't abort the run
        return out_path, str(exc)


def export_ascii(
    items: Sequence[tuple],  # (Dataset, out_path)
    workers: Optional[int] = None,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> tuple[list[Path], list[str]]:
    """Export datasets to ``.dat`` files in parallel.

    Args:
        items: ``(dataset, destination_path)`` pairs.
        workers: Process count (default CPU count - 1; 1 = in-process).
        progress: Called as ``progress(done, total)``.
        cancel: Polled between files; return True to stop early.

    Returns:
        ``(written_paths, error_messages)``.
    """
    tasks = [
        (str(d.path), str(out), d.sample, d.technique, str(d.rel_path))
        for d, out in items
    ]
    total = len(tasks)
    written: list[Path] = []
    errors: list[str] = []
    if total == 0:
        return written, errors

    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 1)

    if workers == 1:
        for i, t in enumerate(tasks, 1):
            if cancel and cancel():
                break
            out, err = _export_one(t)
            (errors.append(f"{out}: {err}") if err else written.append(Path(out)))
            if progress:
                progress(i, total)
        return written, errors

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_export_one, t) for t in tasks]
        done = 0
        for fut in as_completed(futures):
            out, err = fut.result()
            (errors.append(f"{out}: {err}") if err else written.append(Path(out)))
            done += 1
            if progress:
                progress(done, total)
            if cancel and cancel():
                for f in futures:
                    f.cancel()
                break
    return written, errors
