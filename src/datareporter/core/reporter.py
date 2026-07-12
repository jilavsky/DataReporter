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
    scope: Literal["sample", "user", "month", "technique", "file"] = "sample",
    settings: Optional[ReportSettings] = None,
    input_root: Optional[Path] = None,
) -> List[Path]:
    """Produce reports in the requested format(s).

    Args:
        records: Scanned Nexus records.
        output_dir: Directory for generated reports (used as base when neither
            mirror nor add_to_source is enabled, or when only mirror is enabled).
        fmt: One of ``pdf``, ``obsidian``, ``csv``, or ``all``.
        scope: Grouping level for multi-file reports. Supports standard scopes
            (sample, user, month, technique, file).  Mirror and add_to_source are
            controlled via the ``mirror``/``add_to_source`` settings keys.
        settings: Optional full ReportSettings dict to override defaults. When
            provided, its values take precedence over those derived from fmt/scope.
        input_root: The root directory the user scanned.  Required when
            ``add_to_source=True`` in settings; ignored otherwise.

    Returns:
        List of paths to produced report files.
    """
    formats = _parse_formats(fmt)

    # Build base settings from individual params
    base_settings: ReportSettings = {
        "scope": scope,
        "mirror": False,
        "add_to_source": False,
        "formats": formats,
        "pdf_grid": (2, 3),
        "pdf_metadata_summary": True,
        "obsidian_attachments": True,
        "obsidian_md_per_technique": False,
        "csv_delimiter": ",",
        "datasets_per_graph": 1,
    }

    # Merge in any caller-provided settings (takes full precedence)
    if settings is not None:
        base_settings.update(settings)

    return _orchestrate(records, Path(output_dir), base_settings, input_root=input_root)


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
