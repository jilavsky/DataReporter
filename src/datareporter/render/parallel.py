"""Parallel image rendering.

The unit of work is **one output image** (which may overlay several
datasets).  Each worker process opens its HDF5 file(s), reads the curves
and metadata, and renders a PNG.  Results carry the metadata back to the
main process so document writers never have to touch HDF5 themselves.

Deterministic image names (``<dataset uid(s) hash>.png``) give an exact
dataset-to-image mapping — no filename guessing anywhere downstream.
"""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

__all__ = ["RenderTask", "RenderResult", "make_task", "render_all"]


@dataclass
class RenderTask:
    """Render one PNG from one or more HDF5 files."""

    image_id: str                       #: unique id, also the PNG filename stem
    files: list[tuple[str, str]]        #: (dataset uid, absolute HDF5 path)
    title: str
    technique: str
    out_path: str                       #: absolute PNG destination


@dataclass
class RenderResult:
    image_id: str
    out_path: str
    ok: bool
    error: str = ""
    #: dataset uid -> {"label": ..., "metadata": {...}} for every file rendered
    dataset_info: dict[str, dict[str, Any]] = field(default_factory=dict)


def make_task(
    datasets: Sequence,  # Sequence[Dataset]
    title: str,
    technique: str,
    image_dir: Path,
) -> RenderTask:
    """Build a RenderTask for a chunk of datasets sharing one image."""
    joined = "|".join(d.uid for d in datasets)
    image_id = datasets[0].uid if len(datasets) == 1 else hashlib.sha1(joined.encode()).hexdigest()[:12]
    return RenderTask(
        image_id=image_id,
        files=[(d.uid, str(d.path)) for d in datasets],
        title=title,
        technique=technique,
        out_path=str(Path(image_dir) / f"{image_id}.png"),
    )


def _render_one(task: RenderTask) -> RenderResult:
    """Worker entry point — must stay importable at module top level."""
    from datareporter.core.nexus import read_curve
    from datareporter.render.plots import render_image

    curves = []
    info: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for uid, fpath in task.files:
        try:
            c = read_curve(fpath)
            curves.append(c)
            info[uid] = {"label": c.label, "metadata": c.metadata}
        except Exception as exc:  # noqa: BLE001 — collect, don't abort the run
            errors.append(f"{Path(fpath).name}: {exc}")

    if not curves:
        return RenderResult(task.image_id, task.out_path, ok=False,
                            error="; ".join(errors) or "no readable curves")
    try:
        render_image(curves, task.out_path, task.title, task.technique)
    except Exception as exc:  # noqa: BLE001
        return RenderResult(task.image_id, task.out_path, ok=False,
                            error=str(exc), dataset_info=info)
    return RenderResult(task.image_id, task.out_path, ok=True,
                        error="; ".join(errors), dataset_info=info)


def render_all(
    tasks: Sequence[RenderTask],
    workers: Optional[int] = None,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
) -> dict[str, RenderResult]:
    """Render all tasks in parallel; returns ``{image_id: RenderResult}``.

    Args:
        tasks: Work items from :func:`make_task`.
        workers: Process count (default: CPU count - 1, min 1).
            ``workers=1`` renders in-process (useful for tests/debugging).
        progress: Called as ``progress(done, total)`` after each image.
        cancel: Polled between completions; return True to stop early
            (pending work is cancelled, finished images are kept).
    """
    total = len(tasks)
    results: dict[str, RenderResult] = {}
    if total == 0:
        return results

    if workers is None:
        workers = max(1, (os.cpu_count() or 2) - 1)

    if workers == 1:
        for i, t in enumerate(tasks, 1):
            if cancel and cancel():
                break
            results[t.image_id] = _render_one(t)
            if progress:
                progress(i, total)
        return results

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_render_one, t): t for t in tasks}
        done = 0
        for fut in as_completed(futures):
            res = fut.result()
            results[res.image_id] = res
            done += 1
            if progress:
                progress(done, total)
            if cancel and cancel():
                for f in futures:
                    f.cancel()
                break
    return results
