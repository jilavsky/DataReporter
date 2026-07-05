"""Tests for PDF writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from datareporter.core.scanner import NexusRecord
from datareporter.io.pdf_writer import write_pdf


@pytest.fixture()
def sample_records(tmp_path):
    imgs = []
    for i in range(3):
        p = tmp_path / f"sample_{i}.jpg"
        import numpy as np
        from PIL import Image
        arr = (np.random.rand(100, 100, 3) * 255).astype("uint8")
        Image.fromarray(arr).save(str(p))
        imgs.append(p)
    recs = []
    for i, img in enumerate(imgs):
        recs.append(NexusRecord(path=Path(f"f{i}.h5"), filename=f"f{i}.h5", size_bytes=100))
    return recs, tmp_path


def test_write_pdf_creates_file(sample_records, tmp_path):
    recs, _ = sample_records
    out = tmp_path / "out"
    tmp_imgs = tmp_path / "tmp"
    written = write_pdf(recs, out, "test", {"pdf_grid": (2, 3)}, tmp_imgs)
    assert len(written) == 1
    assert written[0].exists()
