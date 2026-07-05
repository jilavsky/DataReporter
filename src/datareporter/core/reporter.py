"""Coordinate report generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import save_images
from datareporter.io.report_writer import (
    save_csv_report,
    save_markdown_report,
    save_pdf_report,
)


def generate_reports(
    records: List[NexusRecord],
    output_dir: str | Path,
    fmt: str = "all",
) -> List[Path]:
    """Produce JPG images and/or PDF/MD/CSV reports."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    produced: List[Path] = []

    if fmt in {"pdf", "all"}:
        produced.append(save_pdf_report(records, out / "report.pdf"))
    if fmt in {"md", "all"}:
        produced.append(save_markdown_report(records, out / "report.md"))
    if fmt in {"csv", "all"}:
        produced.append(save_csv_report(records, out / "report.csv"))

    save_images(records, out / "images")
    return produced
