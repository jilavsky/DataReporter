"""Tests for report orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

from datareporter.core.report_orchestrator import group_records
from datareporter.core.scanner import NexusRecord


def _record(filename, month, user, sample, technique="tech"):
    return NexusRecord(
        path=Path(filename),
        filename=filename,
        size_bytes=100,
        month=month,
        user=user,
        sample=sample,
        technique=technique,
    )


def test_group_by_sample():
    recs = [_record("a.h5", "2026_06", "userA", "s1"), _record("b.h5", "2026_06", "userA", "s2")]
    groups = group_records(recs, "sample")
    assert set(groups.keys()) == {"2026_06/userA/s1", "2026_06/userA/s2"}


def test_group_by_user():
    recs = [_record("a.h5", "2026_06", "userA", "s1"), _record("b.h5", "2026_06", "userB", "s1")]
    groups = group_records(recs, "user")
    assert set(groups.keys()) == {"2026_06/userA", "2026_06/userB"}


def test_group_by_file():
    recs = [_record("a.h5", "2026_06", "userA", "s1"), _record("b.h5", "2026_06", "userA", "s1")]
    groups = group_records(recs, "file")
    assert set(groups.keys()) == {"a.h5", "b.h5"}
