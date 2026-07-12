"""Report-generation pipeline.

Ties everything together::

    datasets --group--> groups --render (parallel)--> images --write--> documents

The pipeline is UI-agnostic: progress is reported through a callback and
cancellation through a polled flag, so the same code drives the GUI, the
CLI, and scripted runs.
"""

from __future__ import annotations

import datetime as _dt
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from typing import Callable, Optional, Sequence

from datareporter.config import ReportConfig
from datareporter.core.grouping import Group, group_datasets, resolve_output_dir
from datareporter.core.model import Dataset
from datareporter.render.parallel import RenderResult, RenderTask, make_task, render_all
from datareporter.writers.ascii_writer import export_ascii
from datareporter.writers.md_writer import MdImage, write_md
from datareporter.writers.pdf_writer import write_pdf

__all__ = ["RunReport", "generate"]

#: progress callback: (phase, done, total); phases: "render", "ascii", "write"
ProgressFn = Callable[[str, int, int], None]
CancelFn = Callable[[], bool]


@dataclass
class RunReport:
    """Outcome of one pipeline run."""

    produced: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    images_rendered: int = 0
    cancelled: bool = False

    def summary(self) -> str:
        parts = [f"{len(self.produced)} file(s) produced",
                 f"{self.images_rendered} image(s) rendered"]
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.cancelled:
            parts.append("run cancelled")
        return ", ".join(parts)


def generate(
    datasets: Sequence[Dataset],
    config: ReportConfig,
    input_root: Optional[Path] = None,
    progress: Optional[ProgressFn] = None,
    cancel: Optional[CancelFn] = None,
) -> RunReport:
    """Run the full pipeline for *datasets* under *config*.

    Args:
        datasets: Selected datasets (from :mod:`datareporter.core.scanner`).
        config: Validated run configuration.
        input_root: Scan root; defaults to the datasets' common root.
            Required for ``mode="source"`` and ``mode="mirror"`` layouts.
        progress: Optional ``progress(phase, done, total)`` callback.
        cancel: Optional poll function; return True to stop early.
    """
    report = RunReport()
    config.validate()
    if not datasets:
        report.errors.append("No datasets selected.")
        return report

    root = Path(input_root) if input_root else datasets[0].root
    groups = group_datasets(datasets, config.scope)
    wants_images = any(f in config.formats for f in ("pdf", "md"))

    image_dir: Optional[Path] = None
    try:
        results: dict[str, RenderResult] = {}
        group_tasks: dict[str, list[tuple[RenderTask, list[Dataset]]]] = {}
        if wants_images:
            image_dir = Path(tempfile.mkdtemp(prefix="datareporter_img_"))
            all_tasks: list[RenderTask] = []
            for grp in groups:
                tasks = _plan_group_images(grp, config.per_graph, image_dir)
                group_tasks[grp.key] = tasks
                all_tasks.extend(t for t, _ in tasks)
            results = render_all(
                all_tasks,
                workers=config.workers,
                progress=(lambda d, t: progress("render", d, t)) if progress else None,
                cancel=cancel,
            )
            report.images_rendered = sum(1 for r in results.values() if r.ok)
            report.errors.extend(
                f"render: {r.error}" for r in results.values() if not r.ok or r.error
            )
            if cancel and cancel():
                report.cancelled = True
                return report

        # ── document assembly ─────────────────────────────────────────
        for gi, grp in enumerate(groups):
            if cancel and cancel():
                report.cancelled = True
                break
            try:
                out_dir, stem = resolve_output_dir(grp, config.mode, config.output_dir, root)
            except ValueError as exc:
                report.errors.append(str(exc))
                break
            if wants_images:
                sections = _build_sections(group_tasks.get(grp.key, []), results)
                if "pdf" in config.formats:
                    images = [(img.png_path, img.caption)
                              for _, imgs in sections for img in imgs]
                    if images:
                        meta_lines = _summary_lines(grp) if config.pdf_summary else ()
                        pdf = write_pdf(images, out_dir / f"{stem}.pdf", grp.title,
                                        grid=config.pdf_grid, metadata_lines=meta_lines)
                        report.produced.append(pdf)
                if "md" in config.formats:
                    if any(imgs for _, imgs in sections):
                        md = write_md(sections, out_dir, stem, grp.title,
                                      show_metadata=config.md_metadata)
                        report.produced.append(md)
            if progress:
                progress("write", gi + 1, len(groups))

        # ── ASCII export ──────────────────────────────────────────────
        if "ascii" in config.formats and not report.cancelled:
            items = []
            for grp in groups:
                try:
                    out_dir, stem = resolve_output_dir(grp, config.mode, config.output_dir, root)
                except ValueError as exc:
                    report.errors.append(str(exc))
                    break
                dat_dir = out_dir if len(grp.datasets) == 1 else out_dir / f"{stem}_ascii"
                for d in grp.datasets:
                    items.append((d, dat_dir / f"{d.name}.dat"))
            written, errs = export_ascii(
                items,
                workers=config.workers,
                progress=(lambda d, t: progress("ascii", d, t)) if progress else None,
                cancel=cancel,
            )
            report.produced.extend(written)
            report.errors.extend(f"ascii: {e}" for e in errs)
            if cancel and cancel():
                report.cancelled = True
    finally:
        if image_dir is not None:
            shutil.rmtree(image_dir, ignore_errors=True)

    return report


# ── helpers ───────────────────────────────────────────────────────────────

def _plan_group_images(
    group: Group,
    per_graph: int,
    image_dir: Path,
) -> list[tuple[RenderTask, list[Dataset]]]:
    """Chunk a group's datasets into render tasks.

    Datasets are chunked *within* each technique (never mixing USAXS with
    WAXS on one graph).  Group datasets are already technique-ordered.
    """
    tasks: list[tuple[RenderTask, list[Dataset]]] = []
    for tech, items in groupby(group.datasets, key=lambda d: d.technique):
        chunk_src = list(items)
        step = max(1, per_graph)
        for i in range(0, len(chunk_src), step):
            chunk = chunk_src[i:i + step]
            if len(chunk) == 1:
                title = chunk[0].name
            else:
                title = f"{group.title} — {tech or 'data'} ({i + 1}–{i + len(chunk)})"
            tasks.append((make_task(chunk, title, tech, image_dir), chunk))
    return tasks


def _build_sections(
    tasks: list[tuple[RenderTask, list[Dataset]]],
    results: dict[str, RenderResult],
) -> list[tuple[str, list[MdImage]]]:
    """Arrange rendered images into per-technique document sections."""
    sections: dict[str, list[MdImage]] = {}
    order: list[str] = []
    for task, chunk in tasks:
        res = results.get(task.image_id)
        if res is None or not res.ok:
            continue
        tech = chunk[0].technique or "data"
        if tech not in sections:
            sections[tech] = []
            order.append(tech)
        if len(chunk) == 1:
            caption = chunk[0].name
        else:
            caption = f"{tech}: {chunk[0].name} … {chunk[-1].name}"
        ds_info = []
        for d in chunk:
            info = res.dataset_info.get(d.uid, {})
            ds_info.append((info.get("label", d.name), info.get("metadata", {})))
        sections[tech].append(MdImage(png_path=Path(res.out_path),
                                      caption=caption, datasets=ds_info))
    multi = len(order) > 1
    return [(tech if multi else "", sections[tech]) for tech in order]


def _summary_lines(group: Group) -> list[str]:
    counts = Counter(d.technique or "other" for d in group.datasets)
    lines = [f"Generated: {_dt.datetime.now():%Y-%m-%d %H:%M}",
             f"Datasets: {len(group.datasets)}"]
    lines += [f"  {tech}: {n}" for tech, n in sorted(counts.items())]
    return lines
