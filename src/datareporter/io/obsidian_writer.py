"""Write Obsidian-compatible Markdown reports with Attachments folders."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, Sequence

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import save_images


def write_obsidian(
    records: Sequence[NexusRecord],
    output_dir: Path,
    group_name: str,
    settings: dict,
    tmp_images: Optional[Path] = None,
    image_cache_dir: Optional[Path] = None,
    image_mapping: Optional[dict[str, str]] = None,
) -> List[Path]:
    """Write Obsidian markdown report with attached images.

    Args:
        records: Records to include in this group.
        output_dir: Where to write the final report (already resolved by caller).
        group_name: Display name for the group (used as folder and title).
        settings: Report settings dict.
        tmp_images: Legacy temp images dir (kept for backward compat).
        image_cache_dir: Directory containing cached images keyed by record hash.
        image_mapping: Mapping of {record_hash: image_path} from cache build.
    """
    # Determine output base path — when mirror/add_to_source is enabled,
    # output_dir already includes the group_name subdirectory (resolved by caller).
    # In flat mode, output_dir is just the user-selected output directory.
    base = output_dir
    attachments = base / "Attachments"
    attachments.mkdir(exist_ok=True)

    # Resolve image files — prefer cached images when available
    if image_cache_dir and image_mapping:
        image_files = _get_cached_images(records, image_mapping)
    elif tmp_images:
        tmp_group = tmp_images / _safe_name(group_name)
        tmp_group.mkdir(parents=True, exist_ok=True)
        image_files = sorted(tmp_group.glob("*.jpg"))
        if not image_files:
            image_files = sorted(save_images(list(records), tmp_group).glob("*.jpg"))
    else:
        # Fallback: generate images directly into a temp dir under output_dir
        tmp_dir = output_dir / ".tmp_images" / _safe_name(group_name)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        image_files = sorted(save_images(list(records), tmp_dir).glob("*.jpg"))

    # Copy images to Attachments folder
    for img_path in image_files:
        shutil.copy2(str(img_path), str(attachments / img_path.name))

    md_lines = [f"# {group_name}\n"]
    for r in records:
        md_lines.append(f"## {r.filename} (`{r.path}`)\n")
        md_lines.append(f"- Size: {r.size_bytes} bytes")
        md_lines.append(f"- Technique: `{r.technique or '-'}`")
        if r.metadata.get("StartTime"):
            md_lines.append(f"- Start: {_decode_val(r.metadata['StartTime'])}")
        if r.metadata.get("SampleTitle"):
            md_lines.append(f"- Title: {_decode_val(r.metadata['SampleTitle'])}")
        data_arrays = "; ".join(_decode_val(k) for k in r.data_arrays.keys())
        if data_arrays:
            md_lines.append(f"- Data: {data_arrays}")

        # Find matching image for this record and embed it
        matched_img = _find_matching_image(r, image_files)
        if matched_img:
            rel = f"Attachments/{matched_img.name}"
            md_lines.append(f"\n![{matched_img.stem}]({rel})\n")

        md_lines.append("")

    # Use group_name as filename (with safe characters) when in flat mode,
    # or use "report.md" when in nested mode (mirror/add_to_source).
    if settings.get("mirror") or settings.get("add_to_source"):
        md_filename = "report.md"
    else:
        md_filename = f"{_safe_name(group_name)}.md"
    
    md_path = base / md_filename
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return [md_path]


def _find_matching_image(record: NexusRecord, image_files: list[Path]) -> Optional[Path]:
    """Find the cached or generated image that corresponds to a record."""
    # Try matching by filename (with common extensions stripped)
    base_name = record.filename.rsplit(".", 1)[0] if "." in record.filename else record.filename

    for img_path in image_files:
        img_stem = img_path.stem.replace(".", "_")
        if base_name.replace(".", "_") in img_stem or img_stem in base_name.replace(".", "_"):
            return img_path

    # Fallback: match by filename prefix (first 10 chars)
    for img_path in image_files:
        if record.filename[:10] in img_path.stem or img_path.stem[:10] in record.filename:
            return img_path

    return None


def _get_cached_images(
    records: Sequence[NexusRecord],
    image_mapping: dict[str, str],
) -> List[Path]:
    """Retrieve cached images for records using the hash mapping."""
    from datareporter.io.image_cache import _record_hash

    cached_paths = []
    for r in records:
        rh = _record_hash(r)
        if rh in image_mapping:
            cached_paths.append(Path(image_mapping[rh]))

    return sorted(cached_paths)


def _safe_name(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_").replace(":", "-").strip("_")


def _decode_val(val) -> str:
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:
            return str(val)
    return str(val)
