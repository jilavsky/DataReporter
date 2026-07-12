"""Public scripting API for DataReporter.

Everything the GUI can do is available here, e.g. for an end-of-cycle
batch script::

    from datareporter import api

    datasets = api.scan("/data/2026/2026-07", select=r"AHM_.*", blanks="exclude")
    report = api.generate(
        datasets,
        scope="sample",
        formats=["pdf", "md"],
        mode="source",
        per_graph=5,
    )
    print(report.summary())
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Sequence

from datareporter.config import ReportConfig
from datareporter.core.model import Dataset
from datareporter.core.pipeline import RunReport
from datareporter.core.pipeline import generate as _generate
from datareporter.core.scanner import filter_datasets
from datareporter.core.scanner import scan as _scan

__all__ = ["scan", "generate", "Dataset", "ReportConfig", "RunReport"]


def scan(
    root: str | Path,
    select: Optional[str] = None,
    blanks: str = "include",
) -> list[Dataset]:
    """Index HDF5 files under *root* (fast — no files are opened).

    Args:
        root: Any level of the data hierarchy (year/month/user/sample).
        select: Optional case-insensitive regex applied to paths relative
            to *root*.
        blanks: ``"include"`` | ``"exclude"`` | ``"only"``.
    """
    datasets = _scan(root)
    if select or blanks != "include":
        datasets = filter_datasets(datasets, select=select, blanks=blanks)
    return datasets


def generate(
    datasets: Sequence[Dataset],
    scope: str = "sample",
    formats: Sequence[str] = ("pdf",),
    mode: str = "source",
    output_dir: Optional[str | Path] = None,
    per_graph: int = 1,
    pdf_grid: tuple[int, int] = (2, 3),
    workers: Optional[int] = None,
    input_root: Optional[str | Path] = None,
    progress: Optional[Callable[[str, int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
    config: Optional[ReportConfig] = None,
) -> RunReport:
    """Generate reports for *datasets*.

    Either pass individual options or a fully built :class:`ReportConfig`
    via *config* (which then wins).  See :class:`ReportConfig` for the
    meaning of each option.
    """
    if config is None:
        config = ReportConfig(
            scope=scope,  # type: ignore[arg-type]
            mode=mode,  # type: ignore[arg-type]
            output_dir=Path(output_dir) if output_dir else None,
            formats=list(formats),
            per_graph=per_graph,
            pdf_grid=pdf_grid,
            workers=workers,
        )
    return _generate(
        datasets,
        config,
        input_root=Path(input_root) if input_root else None,
        progress=progress,
        cancel=cancel,
    )
