from __future__ import annotations

from orbis_diff.models import DiffReport, FunctionMatchEntry, UnmatchedFunctionEntry
from orbis_diff.report import render_report


def test_render_report_identical_binaries_has_no_modified_added_removed():
    report = DiffReport(
        old_path="old.elf",
        new_path="new.elf",
        overall_similarity=1.0,
        overall_confidence=1.0,
        matched=[
            FunctionMatchEntry("sceFoo", "sceFoo", 0x1000, 0x1000, 1.0, 1.0, is_identical=True),
            FunctionMatchEntry("sceBar", "sceBar", 0x2000, 0x2000, 1.0, 1.0, is_identical=True),
        ],
    )
    text = render_report(report)
    # No itemized sections -- only the one-line summary should mention
    # these words (as "Added: 0" / "Removed: 0" counts).
    assert "\nModified:\n" not in text
    assert "\nAdded:\n" not in text
    assert "\nRemoved:\n" not in text
    assert "Matched: 2 (2 identical, 0 modified)" in text
    assert "Added: 0  Removed: 0" in text


def test_render_report_modified_function_shown_with_addresses_and_similarity():
    report = DiffReport(
        old_path="old.elf",
        new_path="new.elf",
        overall_similarity=0.9,
        overall_confidence=0.9,
        matched=[
            FunctionMatchEntry(
                "sceSomething", "sceSomething", 0x123456, 0x123A20, 0.94, 0.9, is_identical=False
            )
        ],
    )
    text = render_report(report)
    assert "Modified:" in text
    assert "sceSomething" in text
    assert "0x123456 -> 0x123a20" in text
    assert "similarity: 94%" in text


def test_render_report_added_and_removed():
    report = DiffReport(
        old_path="old.elf",
        new_path="new.elf",
        overall_similarity=0.5,
        overall_confidence=0.5,
        added=[UnmatchedFunctionEntry("sub_140123000", 0x140123000)],
        removed=[UnmatchedFunctionEntry("sub_140456000", 0x140456000)],
    )
    text = render_report(report)
    assert "Added:" in text
    assert "sub_140123000" in text
    assert "Removed:" in text
    assert "sub_140456000" in text


def test_render_report_show_identical_flag():
    report = DiffReport(
        old_path="old.elf",
        new_path="new.elf",
        overall_similarity=1.0,
        overall_confidence=1.0,
        matched=[FunctionMatchEntry("sceFoo", "sceFoo", 0x1000, 0x1000, 1.0, 1.0, is_identical=True)],
    )
    default_text = render_report(report, show_identical=False)
    verbose_text = render_report(report, show_identical=True)
    assert "Identical (unchanged) matches:" not in default_text
    assert "Identical (unchanged) matches:" in verbose_text
    assert "sceFoo" in verbose_text


def test_render_report_renamed_function_shows_arrow_between_names():
    report = DiffReport(
        old_path="old.elf",
        new_path="new.elf",
        overall_similarity=0.9,
        overall_confidence=0.9,
        matched=[
            FunctionMatchEntry("sub_1000", "sceRenamed", 0x1000, 0x1000, 0.8, 0.8, is_identical=False)
        ],
    )
    text = render_report(report)
    assert "sub_1000 -> sceRenamed" in text
