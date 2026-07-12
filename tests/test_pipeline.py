"""End-to-end pipeline tests (single-process for determinism)."""

from __future__ import annotations

from pathlib import Path

from datareporter import api
from datareporter.config import ReportConfig
from tests.conftest import DATA_DIR


def _cfg(**kw) -> ReportConfig:
    kw.setdefault("workers", 1)
    return ReportConfig(**kw)


def test_sample_scope_source_mode(sample_tree):
    ds = api.scan(sample_tree, blanks="exclude")
    report = api.generate(ds, config=_cfg(scope="sample", mode="source",
                                          formats=["pdf", "md"]))
    assert not report.errors
    assert (sample_tree / "07_01_UserA/S1/S1.pdf").exists()
    assert (sample_tree / "07_01_UserA/S1/S1.md").exists()
    assert (sample_tree / "07_01_UserA/S1/Attachments").is_dir()
    assert (sample_tree / "07_09_UserB/S3/S3.pdf").exists()


def test_mirror_mode(sample_tree, tmp_path):
    out = tmp_path / "vault"
    ds = api.scan(sample_tree, select=r"S1_saxs/")
    report = api.generate(ds, config=_cfg(scope="technique", mode="mirror",
                                          formats=["md"], output_dir=out))
    assert not report.errors
    md = out / "07_01_UserA/S1/S1_saxs/S1_saxs.md"
    assert md.exists()
    # generated tree must not touch the source tree
    assert not (sample_tree / "07_01_UserA/S1/S1_saxs/S1_saxs.md").exists()


def test_flat_mode_names_encode_path(sample_tree, tmp_path):
    out = tmp_path / "flat"
    ds = api.scan(sample_tree, select=r"S2_")
    report = api.generate(ds, config=_cfg(scope="sample", mode="flat",
                                          formats=["pdf"], output_dir=out))
    assert not report.errors
    assert (out / "07_01_UserA_S2.pdf").exists()


def test_per_graph_overlays(sample_tree, tmp_path):
    out = tmp_path / "o"
    ds = api.scan(sample_tree, select=r"S1_usaxs/", blanks="exclude")
    report = api.generate(ds, config=_cfg(scope="sample", mode="flat",
                                          formats=["md"], output_dir=out,
                                          per_graph=3))
    assert not report.errors
    # 3 datasets, 3 per graph -> exactly one attachment image
    assert report.images_rendered == 1


def test_ascii_grouping(sample_tree, tmp_path):
    out = tmp_path / "a"
    ds = api.scan(sample_tree, select=r"S3_usaxs/", blanks="exclude")
    report = api.generate(ds, config=_cfg(scope="sample", mode="flat",
                                          formats=["ascii"], output_dir=out))
    assert not report.errors
    dats = list((out / "07_09_UserB_S3_ascii").glob("*.dat"))
    assert len(dats) == 3


def test_dataset_scope_one_doc_per_file(sample_tree):
    ds = api.scan(sample_tree, select=r"S2_saxs/", blanks="exclude")
    report = api.generate(ds, config=_cfg(scope="dataset", mode="source",
                                          formats=["pdf"]))
    assert not report.errors
    pdfs = list((sample_tree / "07_01_UserA/S2/S2_saxs").glob("*.pdf"))
    assert len(pdfs) == 3


def test_cancel_before_start(sample_tree):
    ds = api.scan(sample_tree)
    report = api.generate(ds, config=_cfg(scope="sample", mode="source",
                                          formats=["pdf"]),
                          cancel=lambda: True)
    assert report.cancelled or not report.produced


def test_config_validation():
    import pytest

    with pytest.raises(ValueError):
        _cfg(mode="mirror").validate()  # no output_dir
    with pytest.raises(ValueError):
        _cfg(formats=["docx"]).validate()
    with pytest.raises(ValueError):
        _cfg(per_graph=0).validate()


def test_smoke_on_repo_example_data(tmp_path):
    """Full run against the real example files checked into the repo."""
    if not DATA_DIR.is_dir():
        import pytest

        pytest.skip("repo example data not present")
    ds = api.scan(DATA_DIR)
    assert ds, "no example data found"
    report = api.generate(ds, config=_cfg(scope="sample", mode="mirror",
                                          formats=["pdf", "md", "ascii"],
                                          output_dir=tmp_path / "out",
                                          per_graph=3))
    assert report.produced
    assert report.images_rendered > 0
