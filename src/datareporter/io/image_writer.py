"""JPG image generation from Nexus data."""

from __future__ import annotations

from pathlib import Path
from typing import List

from datareporter.core.scanner import NexusRecord


def save_images(records: List[NexusRecord], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for idx, record in enumerate(records, start=1):
        try:
            import h5py
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            with h5py.File(str(record.path), "r") as h5:
                datasets = _find_datasets(h5)
                if not datasets:
                    continue
                for dpath in datasets[:4]:
                    try:
                        data = h5[dpath][()]
                        if data is None or len(data) == 0:
                            continue
                        fig, ax = plt.subplots()
                        ax.plot(data)
                        ax.set_title(f"{record.filename}: {dpath}")
                        fig.tight_layout()
                        fig.savefig(output_dir / f"{idx}_{Path(dpath).name}.jpg", dpi=150)
                        plt.close(fig)
                    except Exception:
                        continue
        except Exception:
            continue
    return output_dir


def _find_datasets(h5: "h5py.File", path: str = "/", max_depth: int = 3) -> list[str]:
    found: list[str] = []
    if max_depth <= 0:
        return found
    try:
        group = h5[path]
    except Exception:
        return found
    for key in list(group.keys())[:20]:
        name = f"{path}/{key}"
        try:
            item = group[key]
        except Exception:
            continue
        if hasattr(item, "keys"):
            found.extend(_find_datasets(h5, name, max_depth - 1))
        elif hasattr(item, "shape") and len(item.shape) >= 1:
            found.append(name)
    return found
