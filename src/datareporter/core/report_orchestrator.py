"""Report generation orchestrator."""

from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path
from typing import List, Literal, Optional, Sequence, TypedDict

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import save_images
from datareporter.io.pdf_writer import write_pdf
from datareporter.io.obsidian_writer import write_obsidian
from datareporter.io.csv_writer import write_csv


Scope = Literal["sample", "user", "month", "file"]


class ReportSettings(TypedDict):
    scope: Scope
    formats: List[str]
    pdf_grid: tuple[int, int]
    pdf_metadata_summary: bool
    obsidian_attachments: bool
    obsidian_md_per_technique: bool
    csv_delimiter: str


def group_records(records: Sequence[NexusRecord], scope: Scope) -> dict[str, List[NexusRecord]]:
    groups: dict[str, List[NexusRecord]] = defaultdict(list)
    for r in records:
        if scope == "file":
            key = r.filename
            groups[key].append(r)
            continue

        # Build key from deepest available level upward.
        # If a higher level is empty, skip it and fall back to the next lower level.
        if scope == "month":
            key = r.month or r.user or r.sample or r.technique or "unknown"
        elif scope == "user":
            if r.user:
                key = f"{r.month}/{r.user}" if r.month else r.user
            else:
                key = r.sample or r.technique or "unknown"
        else:
            if r.sample:
                key = "/".join([p for p in [r.month, r.user, r.sample] if p])
            else:
                key = r.technique or "unknown"

        groups[key].append(r)
    return dict(groups)


def generate_reports(
    records: List[NexusRecord],
    output_dir: Path,
    settings: Optional[ReportSettings] = None,
) -> List[Path]:
    if settings is None:
        settings = _default_settings()

    output_dir.mkdir(parents=True, exist_ok=True)
    produced: List[Path] = []

    groups = group_records(records, settings["scope"])
    tmp_images = output_dir / ".tmp_images"
    tmp_images.mkdir(exist_ok=True)

    if "pdf" in settings["formats"]:
        for group_name, group_recs in groups.items():
            produced.extend(write_pdf(group_recs, output_dir, group_name, settings, tmp_images))

    if "obsidian" in settings["formats"]:
        for group_name, group_recs in groups.items():
            produced.extend(write_obsidian(group_recs, output_dir, group_name, settings, tmp_images))

    if "csv" in settings["formats"]:
        produced.append(write_csv(records, output_dir, settings))

    shutil.rmtree(tmp_images, ignore_errors=True)
    return produced


def _default_settings() -> ReportSettings:
    return {
        "scope": "sample",
        "formats": ["pdf"],
        "pdf_grid": (2, 3),
        "pdf_metadata_summary": True,
        "obsidian_attachments": True,
        "obsidian_md_per_technique": False,
        "csv_delimiter": ",",
    }
