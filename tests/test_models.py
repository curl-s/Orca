from __future__ import annotations

import pytest

from orbis_diff.models import DiffReport, FunctionMatchEntry, UnmatchedFunctionEntry


def test_function_match_entry_valid():
    m = FunctionMatchEntry(
        name_old="sceFoo", name_new="sceFoo", addr_old=0x1000, addr_new=0x1010,
        similarity=0.94, confidence=0.9, is_identical=False,
    )
    assert m.similarity == 0.94


@pytest.mark.parametrize("similarity", [-0.1, 1.1])
def test_function_match_entry_rejects_out_of_range_similarity(similarity):
    with pytest.raises(ValueError):
        FunctionMatchEntry(
            name_old="f", name_new="f", addr_old=0, addr_new=0,
            similarity=similarity, confidence=0.5, is_identical=False,
        )


def test_function_match_entry_rejects_negative_address():
    with pytest.raises(ValueError):
        FunctionMatchEntry(
            name_old="f", name_new="f", addr_old=-1, addr_new=0,
            similarity=0.5, confidence=0.5, is_identical=False,
        )


def test_unmatched_function_entry_rejects_negative_address():
    with pytest.raises(ValueError):
        UnmatchedFunctionEntry(name="sub_1", addr=-5)


def test_diff_report_rejects_out_of_range_overall_similarity():
    with pytest.raises(ValueError):
        DiffReport(old_path="a", new_path="b", overall_similarity=2.0, overall_confidence=0.5)


def test_diff_report_modified_and_identical_split():
    identical = FunctionMatchEntry("f", "f", 0, 0, 1.0, 1.0, is_identical=True)
    modified = FunctionMatchEntry("g", "g", 1, 2, 0.5, 0.5, is_identical=False)
    report = DiffReport(
        old_path="old.elf", new_path="new.elf",
        overall_similarity=0.8, overall_confidence=0.7,
        matched=[identical, modified],
    )
    assert report.modified == [modified]
    assert report.identical_count == 1


def test_diff_report_empty_matches():
    report = DiffReport(old_path="a", new_path="b", overall_similarity=1.0, overall_confidence=1.0)
    assert report.modified == []
    assert report.identical_count == 0
    assert report.added == []
    assert report.removed == []
