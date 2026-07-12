"""Obsidian-compatible Markdown writer.

Produces ``<stem>.md`` plus an ``Attachments/`` folder of PNGs, so a
generated folder can be dropped straight into an Obsidian vault.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from datareporter.core.grouping import safe_name

__all__ = ["MdImage", "write_md"]


@dataclass
class MdImage:
    """One image block in the Markdown document."""

    png_path: Path
    caption: str
    #: per-dataset info shown under the image: (label, metadata dict)
    datasets: list[tuple[str, dict[str, Any]]] = field(default_factory=list)


def write_md(
    sections: Sequence[tuple[str, Sequence[MdImage]]],
    out_dir: Path,
    stem: str,
    title: str,
    show_metadata: bool = True,
) -> Path:
    """Write one Markdown document with an Attachments folder.

    Args:
        sections: ``(section_title, images)`` pairs; a section per
            technique when several techniques share the document.
        out_dir: Destination directory (created if missing).
        stem: Filename stem for the ``.md`` file.
        title: Top-level document title.
        show_metadata: Include per-dataset metadata bullet lists.
    """
    out_dir = Path(out_dir)
    attachments = out_dir / "Attachments"
    attachments.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [f"# {title}", ""]
    for section_title, images in sections:
        if section_title:
            lines += [f"## {section_title}", ""]
        for img in images:
            att_name = f"{safe_name(img.caption)}_{img.png_path.stem[:6]}.png"
            try:
                shutil.copy2(str(img.png_path), str(attachments / att_name))
            except OSError:
                lines += [f"*(image missing: {img.caption})*", ""]
                continue
            if img.caption:
                lines += [f"### {img.caption}", ""]
            lines += [f"![{img.caption}](Attachments/{att_name})", ""]
            if show_metadata:
                for label, meta in img.datasets:
                    if meta:
                        pretty = ", ".join(f"{k}: {v}" for k, v in meta.items())
                        lines += [f"- **{label}** — {pretty}"]
                    else:
                        lines += [f"- **{label}**"]
                if img.datasets:
                    lines += [""]

    md_path = out_dir / f"{safe_name(stem)}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path
