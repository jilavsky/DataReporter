"""Tests for Obsidian writer."""

from __future__ import annotations

from pathlib import Path

from datareporter.core.scanner import NexusRecord
from datareporter.io.obsidian_writer import write_obsidian


def test_write_obsidian_creates_report_and_attachments(tmp_path):
    recs = [
        NexusRecord(path=Path("a.h5"), filename="a.h5", size_bytes=100, month="m", user="u", sample="s", technique="t"),
    ]
    out = tmp_path / "out"
    tmp_imgs = tmp_path / "tmp"
    tmp_imgs.mkdir()
    dmy = tmp_imgs / "dummy.jpg"
    dmy.write_bytes(b"")
    written = write_obsidian(recs, out, "m/u/s", {"obsidian_attachments": True}, tmp_imgs)
    assert len(written) == 1
    md = out / "m" / "u" / "s" / "report.md"
    assert md.exists()
    attach = out / "m" / "u" / "s" / "Attachments"
    assert attach.exists()
    content = md.read_text(encoding="utf-8")
    assert "# m/u/s" in content
