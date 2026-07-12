"""Matplotlib rendering of scattering curves.

Per-technique plot styles are defined in :data:`PLOT_STYLES`; adjust a
style in one place and every output format follows.  This module is
imported inside worker processes — keep it free of GUI dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datareporter.core.nexus import Curve

__all__ = ["PLOT_STYLES", "render_image"]

#: Per-technique axis configuration.  ``""`` covers unclassified files.
PLOT_STYLES: dict[str, dict] = {
    "usaxs": {"xscale": "log", "yscale": "log",
              "xlabel": r"Q ($\mathrm{\AA}^{-1}$)", "ylabel": r"Intensity (cm$^{-1}$)"},
    "usaxs_merged": {"xscale": "log", "yscale": "log",
                     "xlabel": r"Q ($\mathrm{\AA}^{-1}$)", "ylabel": r"Intensity (cm$^{-1}$)"},
    "saxs": {"xscale": "log", "yscale": "log",
             "xlabel": r"Q ($\mathrm{\AA}^{-1}$)", "ylabel": r"Intensity (cm$^{-1}$)"},
    "waxs": {"xscale": "linear", "yscale": "log",
             "xlabel": r"Q ($\mathrm{\AA}^{-1}$)", "ylabel": "Intensity (arb.)"},
    "": {"xscale": "log", "yscale": "log", "xlabel": "Q", "ylabel": "Intensity"},
}

#: Distinct colors for overlaid curves (matplotlib tab10).
COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

#: Figure geometry (inches / dpi) — one place to tune output image size.
FIG_SIZE = (6.0, 4.5)
FIG_DPI = 120


def render_image(
    curves: Sequence[Curve],
    out_path: str | Path,
    title: str,
    technique: str = "",
) -> Path:
    """Render one PNG with one or more curves (legend when several)."""
    style = PLOT_STYLES.get(technique, PLOT_STYLES[""])
    fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=FIG_DPI)
    try:
        for idx, c in enumerate(curves):
            color = COLORS[idx % len(COLORS)]
            ax.plot(c.q, c.i, color=color, linewidth=1.2,
                    label=c.label if len(curves) > 1 else None)
        ax.set_xscale(style["xscale"])
        ax.set_yscale(style["yscale"])
        ax.set_xlabel(style["xlabel"])
        ax.set_ylabel(style["ylabel"])
        ax.set_title(title, fontsize=10)
        ax.grid(True, which="both", alpha=0.25, linewidth=0.4)
        if len(curves) > 1:
            ax.legend(fontsize=7, loc="best", framealpha=0.7)
        fig.tight_layout()
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path))
    finally:
        plt.close(fig)
    return out_path
