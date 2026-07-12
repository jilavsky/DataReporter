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
        # Only combine records of the same technique (e.g., USAXS, SAXS, WAXS).
        _technique_groups = _group_by_technique(records)

        with PdfPages(str(out_path)) as pdf:
            for tech_name, tech_records in _technique_groups.items():
                # Resolve cached images for this technique group
                if image_cache_dir and image_mapping:
                    tech_image_files = _get_cached_images(tech_records, image_mapping)
                elif tmp_images:
                    tmp_group = tmp_images / _safe_name(group_name)
                    tmp_group.mkdir(parents=True, exist_ok=True)
                    tech_image_files = sorted(tmp_group.glob("*.jpg"))
                    if not tech_image_files:
                        tech_image_files = sorted(_generate_images(tech_records, tmp_group).glob("*.jpg"))
                else:
                    tmp_dir = output_dir / ".tmp_images" / _safe_name(group_name)
                    tmp_dir.mkdir(parents=True, exist_ok=True)
                    tech_image_files = sorted(_generate_images(tech_records, tmp_dir).glob("*.jpg"))

                if not tech_records:
                    continue

                num_pages = max(1, (len(tech_image_files) + datasets_per_graph - 1) // datasets_per_graph)

                for page_idx in range(num_pages):
                    start = page_idx * datasets_per_graph
                    end = min(start + datasets_per_graph, len(tech_image_files))
                    page_images = tech_image_files[start:end]
                    page_records = tech_records[start:end] if len(tech_records) >= end else tech_records[start:]

                    fig, ax = plt.subplots(figsize=(11.7, 8.3))
                    title = f"{group_name} — {tech_name}" if tech_name != group_name else group_name
                    fig.text(0.01, 0.99, title, va="top", fontsize=14, weight="bold")

                    curves_plotted = 0
                    for i, (img_path, record) in enumerate(zip(page_images, page_records)):
                        try:
                            color = _DARK_COLORS[i % len(_DARK_COLORS)]

                            # Try to plot actual SAS data curves instead of just displaying images
                            q_data = record.data_arrays.get("Q")
                            i_data = record.data_arrays.get("I")

                            if q_data is not None and i_data is not None:
                                # Plot Q vs I as a line curve
                                ax.loglog(q_data, i_data, color=color, linewidth=1.5,
                                         label=_get_clean_filename(record.filename))
                                curves_plotted += 1
                            else:
                                # Fallback to image if no data arrays available
                                ax.imshow(plt.imread(str(img_path)))
                        except Exception as e:
                            print(f"Warning: Failed to plot record {record.filename}: {e}")

                    # Add legend when multiple datasets are combined on one page
                    if len(page_images) > 1 and curves_plotted > 0:
                        handles, labels = ax.get_legend_handles_labels()
                        ax.legend(handles, labels, loc="upper right", fontsize=8)
                    elif len(page_images) > 1:
                        # Fallback legend with cleaned filenames
                        labels = [_get_clean_filename(r.filename) for r in page_records]
                        handles = [plt.Line2D([0], [0], color=_DARK_COLORS[i % len(_DARK_COLORS)], linewidth=2)
                                   for i in range(len(page_images))]
                        ax.legend(handles, labels, loc="upper right", fontsize=8)

                    if curves_plotted > 0:
                        ax.set_xlabel("Q (Å⁻¹)")
                        ax.set_ylabel("Intensity (cm⁻¹)")

                    plt.tight_layout()
                    pdf.savefig(fig, dpi=150)
                    plt.close(fig)

    written.append(out_path)
    return written


def _get_clean_filename(filename: str) -> str:
    """Extract a clean filename without extension for use in legends.
    
    Removes common prefixes like Databroker UUIDs and dates to make labels more readable.
    Examples:
        "2026_07_12_Servis_AM1_saxs_0001.hdf" -> "AM1_saxs"
        "EPON826_1_0050.hdf" -> "EPON826_1"
    """
    # Remove file extension
    name = Path(filename).stem
    
    parts = name.split("_")
    
    # If filename has many parts, clean up leading date/UUID patterns
    if len(parts) > 3:
        cleaned_parts = []
        skip_until_meaningful = True
        
        for part in parts:
            # Skip pure numeric parts at the beginning (date components, IDs)
            if skip_until_meaningful and part.isdigit():
                continue
            
            # Once we hit a non-numeric part, stop skipping
            if skip_until_meaningful:
                skip_until_meaningful = False
            
            cleaned_parts.append(part)
        
        if cleaned_parts:
            name = "_".join(cleaned_parts)
    
    return name


def _group_by_technique(records):
    """Group records by their technique field (e.g., usaxs, saxs, waxs).

    Returns an OrderedDict-like dict preserving insertion order of first
    occurrence per technique.  Records without a technique are grouped under
    the empty string key "".
    """
    groups = {}
    for r in records:
        tech = (r.technique or "").lower() if hasattr(r, "technique") else ""
        groups.setdefault(tech, []).append(r)
    return groups


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
