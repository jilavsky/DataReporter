"""Write landscape PDF reports with image grids."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import (
    _decode as _decode_str,
    save_images as _generate_images,
)


def write_pdf(
    records: Sequence[NexusRecord],
    output_dir: Path,
    group_name: str,
    settings: dict,
    tmp_images: Path,
) -> List[Path]:
    rows, cols = settings.get("pdf_grid", (2, 3))
    images_per_page = rows * cols
    tmp_group = tmp_images / _safe_name(group_name)
    tmp_group.mkdir(parents=True, exist_ok=True)
    image_files = sorted(tmp_group.glob("*.jpg"))

    if not image_files:
        image_files = sorted(_generate_images(records, tmp_group).glob("*.jpg"))

    out_path = output_dir / f"{_safe_name(group_name)}.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(rows, cols, figsize=(11.7, 8.3))
    fig.subplots_adjust(hspace=0.25, wspace=0.15)
    axes = axes.flatten()

    fig.text(0.01, 0.99, group_name, va="top", fontsize=14, weight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    written: List[Path] = []
    for idx, img_path in enumerate(image_files):
        page_idx = idx // images_per_page
        ax_idx = idx % images_per_page

        if ax_idx == 0 and page_idx > 0:
            fig.savefig(str(out_path.parent / f"{out_path.stem}_{page_idx:02d}.pdf"), dpi=150)
            plt.close(fig)
            written.append(out_path.parent / f"{out_path.stem}_{page_idx:02d}.pdf")
            fig, axes = plt.subplots(rows, cols, figsize=(11.7, 8.3))
            axes = axes.flatten()
            fig.text(0.01, 0.99, group_name, va="top", fontsize=14, weight="bold")

        if ax_idx < len(axes):
            ax = axes[ax_idx]
            ax.imshow(plt.imread(str(img_path)))
            ax.axis("off")
            ax.set_title(img_path.stem, fontsize=8, pad=2)

    last_ax_idx = (len(image_files) - 1) % images_per_page if image_files else -1
    for idx in range(last_ax_idx + 1, images_per_page):
        if idx < len(axes):
            axes[idx].axis("off")

    fig.savefig(str(out_path if len(image_files) <= images_per_page else
                    out_path.parent / f"{out_path.stem}_{len(image_files) // images_per_page:02d}.pdf"), dpi=150)
    plt.close(fig)
    written.append(out_path if len(image_files) <= images_per_page else
                   out_path.parent / f"{out_path.stem}_{len(image_files) // images_per_page:02d}.pdf")
    return written


def _safe_name(name: str) -> str:
    name = name.strip("/").strip("_")
    if not name:
        return "report"
    return name.replace("/", "_").replace(" ", "_").replace(":", "-")
