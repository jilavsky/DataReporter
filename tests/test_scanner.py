"""Tests for the fast scanner and dataset filtering."""

from __future__ import annotations

import pytest

from datareporter.core.scanner import filter_datasets, scan


def test_scan_finds_all_files(sample_tree):
    ds = scan(sample_tree)
    # 7 technique folders x (3 + 1 blank) = 28 files
    assert len(ds) == 28


def test_classification(sample_tree):
    ds = scan(sample_tree)
    d = next(x for x in ds if x.name == "S1_meas_0000" and x.technique == "usaxs")
    assert d.sample == "S1"
    assert d.user == "07_01_UserA"
    assert d.month == "2026-07"


def test_usaxs_merged_not_confused_with_usaxs(sample_tree):
    ds = scan(sample_tree)
    merged = [d for d in ds if d.technique == "usaxs_merged"]
    assert len(merged) == 4  # 3 + blank
    assert all(d.sample == "S3" for d in merged)


def test_scan_from_sample_level(sample_tree):
    """Scanning a deeper root still classifies correctly."""
    ds = scan(sample_tree / "07_01_UserA" / "S1")
    assert len(ds) == 12
    assert all(d.sample == "S1" for d in ds)
    assert {d.technique for d in ds} == {"usaxs", "saxs", "waxs"}


def test_regex_filter(sample_tree):
    ds = scan(sample_tree)
    sel = filter_datasets(ds, select=r"S1_usaxs/")
    assert len(sel) == 4
    assert all(d.technique == "usaxs" and d.sample == "S1" for d in sel)


def test_regex_is_case_insensitive(sample_tree):
    ds = scan(sample_tree)
    assert filter_datasets(ds, select=r"s1_USAXS/") == filter_datasets(ds, select=r"S1_usaxs/")


def test_invalid_regex_raises(sample_tree):
    ds = scan(sample_tree)
    with pytest.raises(Exception):
        filter_datasets(ds, select=r"[unclosed")


def test_blank_filtering(sample_tree):
    ds = scan(sample_tree)
    assert len(filter_datasets(ds, blanks="only")) == 7
    assert len(filter_datasets(ds, blanks="exclude")) == 21


def test_uid_is_stable_and_unique(sample_tree):
    ds = scan(sample_tree)
    uids = [d.uid for d in ds]
    assert len(set(uids)) == len(uids)
    assert uids == [d.uid for d in scan(sample_tree)]
