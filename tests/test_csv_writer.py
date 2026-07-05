"""Tests for CSV writer."""

from __future__ import annotations

from pathlib import Path

import csv

from datareporter.core.scanner import NexusRecord
from datareporter.io.csv_writer import write_csv


def test_write_csv_default_delimiter(tmp_path):
    recs = [
        NexusRecord(path=Path("a.h5"), filename="a.h5", size_bytes=100, month="m", user="u", sample="s", technique="t"),
    ]
    out = tmp_path / "out"
    out.mkdir()
    p = write_csv(recs, out, {"csv_delimiter": ","})
    assert p.exists()
    rows = list(csv.reader(p.open(encoding="utf-8")))
    assert rows[0][0] == "filename"
    assert rows[1][0] == "a.h5"


def test_write_csv_tab_delimiter(tmp_path):
    recs = [
        NexusRecord(path=Path("a.h5"), filename="a.h5", size_bytes=100, month="m", user="u", sample="s", technique="t"),
    ]
    out = tmp_path / "out"
    out.mkdir()
    p = write_csv(recs, out, {"csv_delimiter": "\t"})
    rows = list(csv.reader(p.open(encoding="utf-8"), delimiter="\t"))
    assert rows[0][0] == "filename"
    assert rows[1][0] == "a.h5"
