"""PDF, Markdown, and CSV report writers."""

from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from datareporter.core.scanner import NexusRecord


def save_pdf_report(records: List[NexusRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    lines = [f"DataReporter Summary ({len(records)} file(s))", ""]
    for r in records:
        label = r.filename
        if r.sample:
            label = f"{r.sample}/{r.technique or '?'}"
        lines.append(f"- {label}")
        lines.append(f"  user={r.user or '-'} month={r.month or '-'}")
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
        name = r.filename
        if r.sample:
            name = f"{r.sample} / {r.technique or '?'}"
        lines.append(f"## {name}\n")
        lines.append(f"- Path: `{r.path}`")
        lines.append(f"- Month: {r.month or '-'}")
        lines.append(f"- User: {r.user or '-'}")
        lines.append(f"- Size: {r.size_bytes} bytes")
        if r.metadata:
            interesting = [
                k for k in r.metadata
                if k in {
                    "StartTime", "EndTime", "SampleTitle", "Sample_Description",
                    "Sample_Concentration", "wavelength", "SDD", "SRcurrent",
                    "Hutch_Temperature", "UserName",
                }
            ]
            for k in interesting[:15]:
                lines.append(f"- {k}: {r.metadata[k]}")
        if r.data_arrays:
            lines.append(f"- Data arrays: {', '.join(r.data_arrays.keys())}")
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
        writer.writerow([
            "filename", "month", "user", "sample", "technique",
            "size_bytes", "start_time", "sample_title", "data_arrays", "errors",
        ])
        for r in records:
            writer.writerow([
                r.filename,
                r.month,
                r.user,
                r.sample,
                r.technique,
                r.size_bytes,
                r.metadata.get("StartTime"),
                r.metadata.get("SampleTitle"),
                ";".join(r.data_arrays.keys()),
                "; ".join(r.errors),
            ])
    return path
