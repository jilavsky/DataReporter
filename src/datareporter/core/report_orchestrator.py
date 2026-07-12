"""Report generation orchestrator."""

from __future__ import annotations

import shutil
from collections import defaultdict
from pathlib import Path
from typing import List, Literal, Optional, Sequence, TypedDict

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_cache import build_image_cache
from datareporter.io.pdf_writer import write_pdf
from datareporter.io.obsidian_writer import write_obsidian
from datareporter.io.csv_writer import write_csv


Scope = Literal["sample", "user", "month", "technique", "file"]


class ReportSettings(TypedDict):
    scope: Scope
    mirror: bool
    add_to_source: bool
    formats: List[str]
    pdf_grid: tuple[int, int]
    pdf_metadata_summary: bool
    obsidian_attachments: bool
    obsidian_md_per_technique: bool
    csv_delimiter: str
    datasets_per_graph: int


def group_records(records: Sequence[NexusRecord], scope: Scope) -> dict[str, List[NexusRecord]]:
    """Group records by the specified scope level.

    Each group key is a path-like string representing the relative folder
    structure from the data root to the grouping level (e.g.
    ``"2026_06/userA/s1"`` for sample scope).  This same string is used as
    the relative output sub-path when mirror or add_to_source is enabled.
    """
    groups: dict[str, List[NexusRecord]] = defaultdict(list)
    for r in records:
        if scope == "file":
            key = r.filename
            groups[key].append(r)
            continue

        if scope == "technique":
            key = r.technique or r.sample or r.user or r.month or "unknown"
        elif scope == "month":
            key = r.month or r.user or r.sample or r.technique or "unknown"
        elif scope == "user":
            if r.user:
                key = f"{r.month}/{r.user}" if r.month else r.user
            else:
                key = r.sample or r.technique or "unknown"
        else:  # sample
            if r.sample:
                key = "/".join([p for p in [r.month, r.user, r.sample] if p])
            else:
                key = r.technique or "unknown"

        groups[key].append(r)
    return dict(groups)


def _resolve_output_dir(
    group_name: str,
    user_output_dir: Path,
    input_root: Optional[Path],
    mirror: bool,
    add_to_source: bool,
) -> Path:
    """Compute the actual directory where a group's output files should be written.

    Resolution logic (add_to_source takes precedence over mirror):

    1. **add_to_source=True** — writes into the input data tree at the group level.
       Base = ``input_root``.  Result: ``{input_root}/{group_name}/``.
       The user-selected output directory is ignored entirely.

    2. **mirror=True** — reproduces source folder structure under the user's
       chosen output root.  Base = ``user_output_dir``.
       Result: ``{user_output_dir}/{group_name}/``.

    3. **Neither (flat mode)** — all files are written directly into the
       user-selected directory with no subdirectories.
       Result: ``{user_output_dir}/``.

    The ``group_name`` is a path-like string from ``group_records()`` (e.g.
    ``"07_01_Servis/AM1"`` for sample scope).  When mirror or add_to_source
    is enabled, this becomes the relative sub-path under the base directory.
    In flat mode it is used only as a display name / filename stem.

    Args:
        group_name: Path-like group key from ``group_records()``.
        user_output_dir: Directory selected by the user for output.
        input_root: The root directory the user scanned (input location).
            Required when ``add_to_source=True``; ignored otherwise.
        mirror: Reproduce source structure under ``user_output_dir``.
        add_to_source: Write into the input tree at the group level.

    Returns:
        Absolute path to the output sub-directory for this group.
    """
    if add_to_source:
        if not input_root:
            # Fallback — should not happen in normal GUI usage, but guard anyway
            return user_output_dir / group_name
        return input_root / group_name

    if mirror:
        return user_output_dir / group_name

    return user_output_dir


def _get_filename_stem(group_name: str) -> str:
    """Extract a clean filename stem from the group name.

    For scopes that produce hierarchical keys (e.g. ``"07_01_Servis/AM1"``),
    returns only the last segment so filenames stay short and readable in
    flat output mode (e.g. ``"AM1"``, not ``"07_01_Servis_AM1"``).

    For single-segment keys (e.g. scope ``"file"`` producing ``"data.h5"``),
    returns the key as-is.
    """
    parts = group_name.split("/")
    return parts[-1] if len(parts) > 1 else group_name


def _is_flat_mode(mirror: bool, add_to_source: bool) -> bool:
    """Return True when output should be flat (no subdirectories)."""
    return not mirror and not add_to_source


def generate_reports(
    records: List[NexusRecord],
    output_dir: Path,
    settings: Optional[ReportSettings] = None,
    input_root: Optional[Path] = None,
) -> List[Path]:
    """Generate reports for the given records.

    Args:
        records: Scanned Nexus records.
        output_dir: User-selected output directory (used as base when neither
            mirror nor add_to_source is enabled, or when only mirror is enabled).
        settings: Optional full ReportSettings dict to override defaults.
        input_root: The root directory the user scanned.  Required when
            ``add_to_source=True`` in settings; ignored otherwise.

    Returns:
        List of paths to produced report files.
    """
    if settings is None:
        settings = _default_settings()

    mirror = settings.get("mirror", False)
    add_to_source = settings.get("add_to_source", False)

    # Guard: add_to_source requires input_root
    if add_to_source and not input_root:
        raise ValueError(
            "add_to_source=True requires input_root to be provided. "
            "The user must select an input folder."
        )

    output_dir = Path(output_dir)
    if not add_to_source:
        # Only create the output dir when we actually use it as a base
        output_dir.mkdir(parents=True, exist_ok=True)

    # Build image cache once — shared across all formats.
    # When add_to_source is active, place the cache inside the input tree at root.
    if add_to_source:
        image_cache_dir = (input_root or output_dir) / ".image_cache"
    else:
        image_cache_dir = output_dir / ".image_cache"
    image_mapping = build_image_cache(records, image_cache_dir)

    produced: List[Path] = []

    groups = group_records(records, settings["scope"])

    if "pdf" in settings["formats"]:
        for group_name, group_recs in groups.items():
            group_out_dir = _resolve_output_dir(
                group_name=group_name,
                user_output_dir=output_dir,
                input_root=input_root,
                mirror=mirror,
                add_to_source=add_to_source,
            )
            # In flat mode, pass only the last segment as filename stem.
            # In nested modes (mirror/add_to_source), output_dir already has
            # the full path baked in, so pass the full group_name for display.
            if _is_flat_mode(mirror, add_to_source):
                display_name = _get_filename_stem(group_name)
            else:
                display_name = group_name
            produced.extend(write_pdf(
                group_recs, group_out_dir, display_name, settings,
                image_cache_dir=image_cache_dir,
                image_mapping=image_mapping,
            ))

    if "obsidian" in settings["formats"]:
        for group_name, group_recs in groups.items():
            group_out_dir = _resolve_output_dir(
                group_name=group_name,
                user_output_dir=output_dir,
                input_root=input_root,
                mirror=mirror,
                add_to_source=add_to_source,
            )
            if _is_flat_mode(mirror, add_to_source):
                display_name = _get_filename_stem(group_name)
            else:
                display_name = group_name
            produced.extend(write_obsidian(
                group_recs, group_out_dir, display_name, settings,
                image_cache_dir=image_cache_dir,
                image_mapping=image_mapping,
            ))

    if "csv" in settings["formats"]:
        # CSV is always written to the base output directory (flat)
        produced.append(write_csv(records, output_dir, settings))

    # Clean up cache directory
    shutil.rmtree(image_cache_dir, ignore_errors=True)
    return produced


def _default_settings() -> ReportSettings:
    return {
        "scope": "sample",
        "mirror": False,
        "add_to_source": False,
        "formats": ["pdf"],
        "pdf_grid": (2, 3),
        "pdf_metadata_summary": True,
        "obsidian_attachments": True,
        "obsidian_md_per_technique": False,
        "csv_delimiter": ",",
        "datasets_per_graph": 1,
    }


