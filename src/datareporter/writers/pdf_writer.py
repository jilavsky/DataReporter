"""PDF assembly: grids of pre-rendered PNG images, r x c per page."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

__all__ = ["write_pdf"]

#: Landscape A4 in inches.
_PAGE_SIZE = (11.69, 8.27)


def write_pdf(
    images: Sequence[tuple[Path, str]],
    out_path: Path,
    title: str,
    grid: tuple[int, int] = (2, 3),
    metadata_lines: Sequence[str] = (),
) -> Path:
    """Write a multi-page landscape PDF of image grids.

    Args:
        images: ``(png_path, caption)`` pairs, in display order.
        out_path: Destination PDF path (parent dirs are created).
        title: Document title, shown on top of every page.
        grid: ``(rows, cols)`` images per page.
        metadata_lines: Optional text lines for a leading summary page.
    """
    from matplotlib.backends.backend_pdf import PdfPages

    rows, cols = max(1, grid[0]), max(1, grid[1])
    per_page = rows * cols
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with PdfPages(str(out_path)) as pdf:
        if metadata_lines:
            fig = plt.figure(figsize=_PAGE_SIZE)
            fig.text(0.05, 0.95, title, fontsize=16, weight="bold", va="top")
            fig.text(0.05, 0.88, "\n".join(metadata_lines), fontsize=9,
                     va="top", family="monospace")
            pdf.savefig(fig)
            plt.close(fig)

        for start in range(0, len(images), per_page):
            page = images[start:start + per_page]
            fig, axes = plt.subplots(rows, cols, figsize=_PAGE_SIZE)
            axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
            fig.suptitle(title, fontsize=12, weight="bold")
            for ax in axes_flat:
                ax.axis("off")
            for ax, (png, caption) in zip(axes_flat, page):
                try:
                    ax.imshow(plt.imread(str(png)))
                except (OSError, ValueError):
                    ax.text(0.5, 0.5, f"missing image\n{caption}",
                            ha="center", va="center", fontsize=8)
                if caption:
                    ax.set_title(caption, fontsize=7, pad=2)
            fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.02,
                                hspace=0.18, wspace=0.05)
            pdf.savefig(fig, dpi=150)
            plt.close(fig)

    return out_path
