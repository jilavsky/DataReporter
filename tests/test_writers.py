"""Tests for the PDF, Markdown, and ASCII writers."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from datareporter.core.nexus import Curve
from datareporter.core.scanner import scan
from datareporter.render.plots import render_image
from datareporter.writers.ascii_writer import export_ascii
from datareporter.writers.md_writer import MdImage, write_md
from datareporter.writers.pdf_writer import write_pdf


def _png(tmp_path: Path, name: str = "img.png") -> Path:
    q = np.geomspace(1e-4, 1, 20)
    return render_image([Curve(q=q, i=q ** -2, label="x")], tmp_path / name, "t", "saxs")


def test_render_image_creates_png(tmp_path):
    p = _png(tmp_path)
    assert p.exists() and p.stat().st_size > 0


def test_write_pdf_page_count(tmp_path):
    imgs = [(_png(tmp_path, f"i{k}.png"), f"cap{k}") for k in range(7)]
    out = write_pdf(imgs, tmp_path / "r.pdf", "Title", grid=(2, 3),
                    metadata_lines=["line one"])
    data = out.read_bytes()
    # 7 images at 6/page -> 2 grid pages + 1 summary page = 3 pages
    assert data.count(b"/Type /Page ") == 3 or data.count(b"/Type/Page") >= 3


def test_write_md_structure(tmp_path):
    png = _png(tmp_path)
    img = MdImage(png_path=png, caption="my image",
                  datasets=[("ds1", {"Title": "abc"})])
    md = write_md([("usaxs", [img])], tmp_path / "out", "S1", "Sample S1")
    text = md.read_text()
    assert text.startswith("# Sample S1")
    assert "## usaxs" in text
    assert "![my image](Attachments/" in text
    assert "Title: abc" in text
    att = list((tmp_path / "out" / "Attachments").glob("*.png"))
    assert len(att) == 1


def test_ascii_export(sample_tree, tmp_path):
    ds = scan(sample_tree)[:3]
    items = [(d, tmp_path / f"{d.name}.dat") for d in ds]
    written, errors = export_ascii(items, workers=1)
    assert not errors
    assert len(written) == 3
    lines = written[0].read_text().splitlines()
    header = [l for l in lines if l.startswith("#")]
    data = [l for l in lines if not l.startswith("#")]
    assert any("Technique:" in h for h in header)
    assert any("Columns:" in h for h in header)
    assert len(data[0].split()) == 3
    np.loadtxt(str(written[0]))  # parses cleanly
