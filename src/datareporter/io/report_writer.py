"""PDF, Markdown, and CSV report writers."""

from __future__ import annotations

from pathlib import Path
from typing import List

from datareporter.core.scanner import NexusRecord


def save_pdf_report(records: List[NexusRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    lines = [f"DataReporter Summary ({len(records)} file(s))", ""]
    for r in records:
        lines.append(f"- {r.filename} ({r.size_bytes} bytes)")
        if r.errors:
            lines.append(f"  errors: {', '.join(r.errors)}")
    ax.text(0.05, 0.95, "\n".join(lines), va="top", fontsize=10, family="monospace")
    fig.savefig(str(path), dpi=150)
    plt.close(fig)
    return path


def save_markdown_report(records: List[NexusRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# DataReporter Summary\n", f"Files scanned: {len(records)}\n"]
    for r in records:
        lines.append(f"## {r.filename}\n")
        lines.append(f"- Path: `{r.path}`")
        lines.append(f"- Size: {r.size_bytes} bytes")
        if r.entries:
            lines.append(f"- Entries: {', '.join(r.entries[:20])}")
        if r.errors:
            lines.append(f"- Errors: {', '.join(r.errors)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def save_csv_report(records: List[NexusRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "path", "size_bytes", "entry_count", "errors"])
        for r in records:
            writer.writerow([
                r.filename,
                str(r.path),
                r.size_bytes,
                len(r.entries),
                "; ".join(r.errors),
            ])
    return path
