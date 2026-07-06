"""Coordinate report generation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional

from datareporter.core.report_orchestrator import ReportSettings, generate_reports as _orchestrate
from datareporter.core.scanner import NexusRecord


def generate_reports(
    records: List[NexusRecord],
    output_dir: str | Path,
    fmt: str = "all",
    scope: Literal["sample", "user", "month", "file"] = "sample",
) -> List[Path]:
    """Produce reports in the requested format(s).

    Args:
        records: Scanned Nexus records.
        output_dir: Directory for generated reports.
        fmt: One of ``pdf``, ``obsidian``, ``csv``, or ``all``.
        scope: Grouping level for multi-file reports.
    """
    formats = _parse_formats(fmt)
    settings: ReportSettings = {
        "scope": scope,
        "formats": formats,
        "pdf_grid": (2, 3),
        "pdf_metadata_summary": True,
        "obsidian_attachments": True,
        "obsidian_md_per_technique": False,
        "csv_delimiter": ",",
    }
    return _orchestrate(records, Path(output_dir), settings)


def _parse_formats(fmt: str) -> List[str]:
    if fmt == "all":
        return ["pdf", "obsidian", "csv"]
    parts = [p.strip() for p in fmt.split(",")]
    mapping = {"pdf": "pdf", "md": "obsidian", "csv": "csv", "obsidian": "obsidian", "markdown": "obsidian"}
    resolved = []
    for p in parts:
        val = mapping.get(p)
        if val is not None and val not in resolved:
            resolved.append(val)
    return resolved or ["pdf"]
