"""Tests for scope grouping and output-path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from datareporter.core.grouping import group_datasets, resolve_output_dir, safe_name
from datareporter.core.scanner import scan


def test_group_by_sample(sample_tree):
    ds = scan(sample_tree)
    groups = group_datasets(ds, "sample")
    assert {g.stem for g in groups} == {"S1", "S2", "S3"}
    s1 = next(g for g in groups if g.stem == "S1")
    assert len(s1.datasets) == 12
    # ordered by technique: usaxs before saxs before waxs
    techs = [d.technique for d in s1.datasets]
    assert techs.index("usaxs") < techs.index("saxs") < techs.index("waxs")


def test_group_by_technique(sample_tree):
    ds = scan(sample_tree)
    groups = group_datasets(ds, "technique")
    assert len(groups) == 7
    assert all(len(g.datasets) == 4 for g in groups)


def test_group_by_dataset(sample_tree):
    ds = scan(sample_tree)
    groups = group_datasets(ds, "dataset")
    assert len(groups) == len(ds)
    assert all(len(g.datasets) == 1 for g in groups)


def test_group_by_user(sample_tree):
    ds = scan(sample_tree)
    groups = group_datasets(ds, "user")
    assert {g.stem for g in groups} == {"07_01_UserA", "07_09_UserB"}


def test_resolve_source_mode(sample_tree):
    ds = scan(sample_tree)
    g = next(x for x in group_datasets(ds, "sample") if x.stem == "S1")
    out_dir, stem = resolve_output_dir(g, "source", None, Path(sample_tree))
    assert out_dir == Path(sample_tree) / "07_01_UserA" / "S1"
    assert stem == "S1"


def test_resolve_mirror_mode(sample_tree):
    ds = scan(sample_tree)
    g = next(x for x in group_datasets(ds, "sample") if x.stem == "S1")
    out_dir, stem = resolve_output_dir(g, "mirror", Path("/out"), Path(sample_tree))
    assert out_dir == Path("/out/07_01_UserA/S1")


def test_resolve_flat_mode(sample_tree):
    ds = scan(sample_tree)
    g = next(x for x in group_datasets(ds, "sample") if x.stem == "S1")
    out_dir, stem = resolve_output_dir(g, "flat", Path("/out"), Path(sample_tree))
    assert out_dir == Path("/out")
    assert stem == "07_01_UserA_S1"  # path baked into the name


def test_mirror_without_output_dir_raises(sample_tree):
    ds = scan(sample_tree)
    g = group_datasets(ds, "sample")[0]
    with pytest.raises(ValueError):
        resolve_output_dir(g, "mirror", None, Path(sample_tree))


def test_safe_name():
    assert safe_name("a/b c:d") == "a_b_c_d"
    assert safe_name("x…y") == "x_y"
    assert safe_name("") == "report"
