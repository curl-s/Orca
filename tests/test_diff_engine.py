from __future__ import annotations

import pytest

from orbis_diff.config import OrbisDiffConfig
from orbis_diff.diff_engine import run_bindiff
from orbis_diff.errors import DiffEngineError


def _cfg(tmp_path) -> OrbisDiffConfig:
    return OrbisDiffConfig(work_dir=tmp_path / "work")


def _binexport_pair(tmp_path):
    old = tmp_path / "old.BinExport"
    new = tmp_path / "new.BinExport"
    old.write_bytes(b"fake-old")
    new.write_bytes(b"fake-new")
    return old, new


def test_identical_binaries_all_matches_identical(tmp_path, fake_bindiff):
    FakeFunction = fake_bindiff["FakeFunction"]
    FakeMatch = fake_bindiff["FakeMatch"]
    old_be, new_be = _binexport_pair(tmp_path)

    fake_bindiff["matches"] = [
        (FakeFunction("sceFoo", 0x1000), FakeFunction("sceFoo", 0x1000), FakeMatch(0x1000, 0x1000, 1.0, 1.0)),
        (FakeFunction("sceBar", 0x2000), FakeFunction("sceBar", 0x2000), FakeMatch(0x2000, 0x2000, 1.0, 1.0)),
    ]
    fake_bindiff["similarity"] = 1.0
    fake_bindiff["confidence"] = 1.0

    scratch = tmp_path / "scratch.BinDiff"
    final = tmp_path / "stable" / "final.BinDiff"
    cfg = _cfg(tmp_path)

    report = run_bindiff(old_be, new_be, scratch, final, "old.elf", "new.elf", cfg)

    assert len(report.matched) == 2
    assert report.modified == []
    assert report.identical_count == 2
    assert report.added == []
    assert report.removed == []
    assert final.exists()
    assert not scratch.exists()  # moved, not copied


def test_modified_binaries_below_threshold_reported_as_modified(tmp_path, fake_bindiff):
    FakeFunction = fake_bindiff["FakeFunction"]
    FakeMatch = fake_bindiff["FakeMatch"]
    old_be, new_be = _binexport_pair(tmp_path)

    fake_bindiff["matches"] = [
        (
            FakeFunction("sceSomething", 0x123456),
            FakeFunction("sceSomething", 0x123A20),
            FakeMatch(0x123456, 0x123A20, 0.94, 0.9),
        )
    ]
    fake_bindiff["similarity"] = 0.94
    fake_bindiff["confidence"] = 0.9

    cfg = _cfg(tmp_path)
    report = run_bindiff(
        old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg
    )

    assert len(report.modified) == 1
    m = report.modified[0]
    assert m.name_old == "sceSomething"
    assert m.addr_old == 0x123456
    assert m.addr_new == 0x123A20
    assert m.similarity == pytest.approx(0.94)


def test_added_and_removed_functions(tmp_path, fake_bindiff):
    FakeFunction = fake_bindiff["FakeFunction"]
    old_be, new_be = _binexport_pair(tmp_path)

    fake_bindiff["removed"] = [FakeFunction("sub_140456000", 0x140456000)]
    fake_bindiff["added"] = [FakeFunction("sub_140123000", 0x140123000)]
    fake_bindiff["similarity"] = 0.5
    fake_bindiff["confidence"] = 0.5

    cfg = _cfg(tmp_path)
    report = run_bindiff(
        old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg
    )

    assert len(report.added) == 1
    assert report.added[0].name == "sub_140123000"
    assert report.added[0].addr == 0x140123000
    assert len(report.removed) == 1
    assert report.removed[0].name == "sub_140456000"


def test_unmatched_function_without_name_falls_back_to_sub_addr(tmp_path, fake_bindiff):
    FakeFunction = fake_bindiff["FakeFunction"]
    old_be, new_be = _binexport_pair(tmp_path)
    fake_bindiff["added"] = [FakeFunction(None, 0xDEAD)]

    cfg = _cfg(tmp_path)
    report = run_bindiff(
        old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg
    )
    assert report.added[0].name == "sub_dead"


def test_missing_binexport_input_raises_diff_engine_error(tmp_path, fake_bindiff):
    old_be = tmp_path / "does_not_exist.BinExport"
    new_be = tmp_path / "new.BinExport"
    new_be.write_bytes(b"x")
    cfg = _cfg(tmp_path)

    with pytest.raises(DiffEngineError, match="missing"):
        run_bindiff(old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg)


def test_bindiff_not_installed_raises_clear_error(tmp_path, monkeypatch):
    # No fake_bindiff fixture used here -> `import bindiff` fails for real
    # (unless python-bindiff happens to be installed in the test env, in
    # which case we force the import to fail to keep this test hermetic).
    import sys
    monkeypatch.setitem(sys.modules, "bindiff", None)  # forces ImportError on `import bindiff`
    old_be, new_be = _binexport_pair(tmp_path)
    cfg = _cfg(tmp_path)

    with pytest.raises(DiffEngineError, match="python-bindiff is not installed"):
        run_bindiff(old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg)


def test_differ_not_found_raises_clear_error(tmp_path, fake_bindiff):
    fake_bindiff["installation_ok"] = False
    old_be, new_be = _binexport_pair(tmp_path)
    cfg = _cfg(tmp_path)

    with pytest.raises(DiffEngineError, match="differ' binary was not found"):
        run_bindiff(old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg)


def test_differ_raises_during_diff_is_wrapped(tmp_path, fake_bindiff):
    fake_bindiff["raise_on_diff"] = RuntimeError("differ crashed")
    old_be, new_be = _binexport_pair(tmp_path)
    cfg = _cfg(tmp_path)
    scratch = tmp_path / "s.BinDiff"

    with pytest.raises(DiffEngineError, match="differ crashed"):
        run_bindiff(old_be, new_be, scratch, tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg)

    # No broken/partial .BinDiff left at the stable location
    assert not (tmp_path / "f.BinDiff").exists()


def test_no_diff_result_raises_clear_error(tmp_path, fake_bindiff, monkeypatch):
    old_be, new_be = _binexport_pair(tmp_path)
    cfg = _cfg(tmp_path)

    import orbis_diff.diff_engine as diff_engine_module
    import sys
    bindiff_module = sys.modules["bindiff"]
    monkeypatch.setattr(bindiff_module.BinDiff, "from_binexport_files", classmethod(lambda cls, *a, **k: None))

    with pytest.raises(DiffEngineError, match="no diff result"):
        run_bindiff(old_be, new_be, tmp_path / "s.BinDiff", tmp_path / "f.BinDiff", "old.elf", "new.elf", cfg)
