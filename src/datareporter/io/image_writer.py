"""JPG image generation from Nexus data."""

from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datareporter.core.scanner import NexusRecord


def _decode(value):
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return str(value)
    return value


def save_images(records: List[NexusRecord], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, record in enumerate(records, start=1):
        try:
            x = None
            y = None
            x_label = "index"
            y_label = "value"

            q = record.data_arrays.get("entry/sasdata/Q")
            i = record.data_arrays.get("entry/sasdata/I")
            if q is not None and i is not None:
                x, y, x_label, y_label = q, i, "Q", "I"
            else:
                bq = record.data_arrays.get("entry/Blank_data/Q")
                bi = record.data_arrays.get("entry/Blank_data/Intensity")
                if bq is not None and bi is not None:
                    x, y, x_label, y_label = bq, bi, "Q", "Blank Intensity"

            if x is None or y is None:
                continue

            fig, ax = plt.subplots()
            ax.loglog(x, y)
            title_parts = []
            if record.sample:
                title_parts.append(record.sample)
            if record.technique:
                title_parts.append(record.technique)
            if record.metadata.get("SampleTitle"):
                title_parts.append(_decode(record.metadata["SampleTitle"]))
            ax.set_title(" / ".join(title_parts) or record.filename)
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
            fig.tight_layout()
            safe_name = record.filename.replace(" ", "_")
            fig.savefig(output_dir / f"{idx:03d}_{safe_name}.jpg", dpi=150)
            plt.close(fig)
        except Exception:
            continue
    return output_dir
