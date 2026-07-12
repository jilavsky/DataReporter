"""Write landscape PDF reports with image grids."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datareporter.core.scanner import NexusRecord
from datareporter.io.image_writer import save_images as _generate_images


# Color cycle for multi-dataset graphs (10 distinct colors)
_DARK_COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
    "#7f7f7f",  # gray
    "#bcbd22",  # olive
    "#17becf",  # cyan
]


def write_pdf(
    records: Sequence[NexusRecord],
    output_dir: Path,
    group_name: str,
    settings: dict,
    tmp_images: Optional[Path] = None,
    image_cache_dir: Optional[Path] = None,
    image_mapping: Optional[dict[str, str]] = None,
) -> List[Path]:
    """Write PDF report with optional multi-dataset graphs.

    Args:
        records: Records to include in this group.
        output_dir: Where to write the final PDF.
        group_name: Display name for the group (used in title and filename).
        settings: Report settings dict.
        tmp_images: Legacy temp images dir (kept for backward compat).
        image_cache_dir: Directory containing cached images keyed by record hash.
        image_mapping: Mapping of {record_hash: image_path} from cache build.
    """
    datasets_per_graph = settings.get("datasets_per_graph", 1)
    rows, cols = settings.get("pdf_grid", (2, 3))
    images_per_page = rows * cols

    # Resolve image files — prefer cached images when available
    if image_cache_dir and image_mapping:
        image_files = _get_cached_images(records, image_mapping)
    elif tmp_images:
        tmp_group = tmp_images / _safe_name(group_name)
        tmp_group.mkdir(parents=True, exist_ok=True)
        image_files = sorted(tmp_group.glob("*.jpg"))
        if not image_files:
            image_files = sorted(_generate_images(records, tmp_group).glob("*.jpg"))
    else:
        # Fallback: generate images directly into a temp dir under output_dir
        tmp_dir = output_dir / ".tmp_images" / _safe_name(group_name)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        image_files = sorted(_generate_images(records, tmp_dir).glob("*.jpg"))

    from matplotlib.backends.backend_pdf import PdfPages

    out_path = output_dir / f"{_safe_name(group_name)}.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []

    if datasets_per_graph <= 1:
        # Original behavior: one image per cell in a grid layout.
        with PdfPages(str(out_path)) as pdf:
            fig, axes = plt.subplots(rows, cols, figsize=(11.7, 8.3))
            fig.subplots_adjust(hspace=0.25, wspace=0.15)
            axes_flat = axes.flatten()

            for idx in range(len(image_files)):
                ax_idx = idx % images_per_page
                if ax_idx == 0 and idx > 0:
                    pdf.savefig(fig, dpi=150)
                    plt.close(fig)
                    fig, axes = plt.subplots(rows, cols, figsize=(11.7, 8.3))
                    fig.subplots_adjust(hspace=0.25, wspace=0.15)
                    axes_flat = axes.flatten()

                ax = axes_flat[ax_idx]
                ax.imshow(plt.imread(str(image_files[idx])))
                ax.axis("off")
                ax.set_title(image_files[idx].stem, fontsize=8, pad=2)

            # Blank out remaining cells on the last page
            last_ax_idx = (len(image_files) - 1) % images_per_page if image_files else -1
            for idx in range(last_ax_idx + 1, images_per_page):
                if idx < len(axes_flat):
                    axes_flat[idx].axis("off")

            pdf.savefig(fig, dpi=150)
            plt.close(fig)

    else:
        # Multi-dataset mode: combine N datasets per graph with colored curves and legends.
        num_pages = max(1, (len(image_files) + datasets_per_graph - 1) // datasets_per_graph)

        with PdfPages(str(out_path)) as pdf:
            for page_idx in range(num_pages):
                start = page_idx * datasets_per_graph
                end = min(start + datasets_per_graph, len(image_files))
                page_images = image_files[start:end]

                fig, ax = plt.subplots(figsize=(11.7, 8.3))
                fig.text(0.01, 0.99, group_name, va="top", fontsize=14, weight="bold")

                for i, img_path in enumerate(page_images):
                    color = _DARK_COLORS[i % len(_DARK_COLORS)]
                    ax.imshow(plt.imread(str(img_path)))
                    ax.set_title(img_path.stem, fontsize=10, pad=5)

                # Add legend when multiple datasets are combined on one page
                if len(page_images) > 1:
                    labels = [img.stem for img in page_images]
                    handles = [plt.Line2D([0], [0], color=_DARK_COLORS[i % len(_DARK_COLORS)], linewidth=2)
                               for i in range(len(page_images))]
                    ax.legend(handles, labels, loc="upper right", fontsize=8)

                ax.axis("off")
                plt.tight_layout()
                pdf.savefig(fig, dpi=150)
                plt.close(fig)

    written.append(out_path)
    return written


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
    name = name.strip("/").strip("_")
    if not name:
        return "report"
    return name.replace("/", "_").replace(" ", "_").replace(":", "-")
