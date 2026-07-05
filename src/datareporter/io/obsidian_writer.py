"""Write Obsidian-compatible Markdown reports with Attachments folders."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Sequence

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import save_images


def write_obsidian(
    records: Sequence[NexusRecord],
    output_dir: Path,
    group_name: str,
    settings: dict,
    tmp_images: Path,
) -> List[Path]:
    parts = group_name.split("/")
    base = output_dir
    for p in parts:
        base = base / p
    base.mkdir(parents=True, exist_ok=True)

    attachments = base / "Attachments"
    attachments.mkdir(exist_ok=True)
    tmp_group = tmp_images / _safe_name(group_name)
    tmp_group.mkdir(parents=True, exist_ok=True)
    image_files = sorted(tmp_group.glob("*.jpg"))
    if not image_files:
        image_files = sorted(save_images(list(records), tmp_group).glob("*.jpg"))

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
        for img_path in image_files:
            img_stem = img_path.stem.replace(".", "_")
            if r.filename.replace(".", "_") in img_stem:
                rel = f"Attachments/{img_path.name}"
                md_lines.append(f"\n![{img_path.stem}]({rel})\n")
                break
        md_lines.append("")

    md_path = base / "report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return [md_path]


def _safe_name(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_").replace(":", "-").strip("_")


def _decode_val(val) -> str:
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except Exception:
            return str(val)
    return str(val)
