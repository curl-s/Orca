from __future__ import annotations

import pytest

import orbis_diff.pipeline as pipeline_module
from orbis_diff.config import OrbisDiffConfig
from orbis_diff.errors import DiffEngineError, GhidraExportError, InputFileError
from orbis_diff.ghidra_export import ExportResult
from orbis_diff.models import DiffReport
from orbis_diff.pipeline import diff_binaries


def _cfg(tmp_path):
    return OrbisDiffConfig(work_dir=tmp_path / "work")


def test_missing_old_binary_raises_input_file_error(tmp_path):
    new = tmp_path / "new.elf"
    new.write_bytes(b"data")
    with pytest.raises(InputFileError, match="old binary not found"):
        diff_binaries(tmp_path / "missing_old.elf", new, _cfg(tmp_path))


def test_missing_new_binary_raises_input_file_error(tmp_path):
    old = tmp_path / "old.elf"
    old.write_bytes(b"data")
    with pytest.raises(InputFileError, match="new binary not found"):
        diff_binaries(old, tmp_path / "missing_new.elf", _cfg(tmp_path))


def test_empty_input_file_raises_input_file_error(tmp_path):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"")
    new.write_bytes(b"data")
    with pytest.raises(InputFileError, match="is empty"):
        diff_binaries(old, new, _cfg(tmp_path))


def test_directory_as_input_raises_input_file_error(tmp_path):
    old_dir = tmp_path / "old_dir"
    old_dir.mkdir()
    new = tmp_path / "new.elf"
    new.write_bytes(b"data")
    with pytest.raises(InputFileError, match="not a regular file"):
        diff_binaries(old_dir, new, _cfg(tmp_path))


def test_ghidra_failure_propagates_as_ghidra_export_error(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"data")
    new.write_bytes(b"data2")

    def boom(binary, cfg):
        raise GhidraExportError("Ghidra import/analysis failed (exit 1)")

    monkeypatch.setattr(pipeline_module, "export_binary_to_binexport", boom)

    with pytest.raises(GhidraExportError):
        diff_binaries(old, new, _cfg(tmp_path), validate_config=False)


def test_bindiff_failure_propagates_as_diff_engine_error(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"data")
    new.write_bytes(b"data2")

    def fake_export(binary, cfg):
        be = tmp_path / f"{binary.name}.BinExport"
        be.write_bytes(b"exported")
        return ExportResult(binary_path=binary, binexport_path=be, ghidra_log_dir=tmp_path)

    def fake_run_bindiff(*args, **kwargs):
        raise DiffEngineError("BinDiff differ crashed")

    monkeypatch.setattr(pipeline_module, "export_binary_to_binexport", fake_export)
    monkeypatch.setattr(pipeline_module, "run_bindiff", fake_run_bindiff)

    with pytest.raises(DiffEngineError):
        diff_binaries(old, new, _cfg(tmp_path), validate_config=False)


def test_new_binary_export_not_attempted_if_old_fails(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"data")
    new.write_bytes(b"data2")

    calls = []

    def fake_export(binary, cfg):
        calls.append(binary.name)
        if binary.name == "old.elf":
            raise GhidraExportError("boom")
        return ExportResult(binary_path=binary, binexport_path=tmp_path / "x.BinExport", ghidra_log_dir=tmp_path)

    monkeypatch.setattr(pipeline_module, "export_binary_to_binexport", fake_export)

    with pytest.raises(GhidraExportError):
        diff_binaries(old, new, _cfg(tmp_path), validate_config=False)

    assert calls == ["old.elf"]  # new.elf export never attempted


def test_successful_pipeline_returns_diff_report(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"data")
    new.write_bytes(b"data2")

    def fake_export(binary, cfg):
        be = tmp_path / f"{binary.name}.BinExport"
        be.write_bytes(b"exported")
        return ExportResult(binary_path=binary, binexport_path=be, ghidra_log_dir=tmp_path)

    expected_report = DiffReport(
        old_path=str(old), new_path=str(new), overall_similarity=1.0, overall_confidence=1.0
    )

    def fake_run_bindiff(*args, **kwargs):
        return expected_report

    monkeypatch.setattr(pipeline_module, "export_binary_to_binexport", fake_export)
    monkeypatch.setattr(pipeline_module, "run_bindiff", fake_run_bindiff)

    report = diff_binaries(old, new, _cfg(tmp_path), validate_config=False)
    assert report is expected_report


def test_validate_config_true_by_default_fails_fast_without_running_ghidra(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"data")
    new.write_bytes(b"data2")

    cfg = _cfg(tmp_path)  # nothing configured -> validate() will fail

    called = {"export": False}

    def fake_export(binary, cfg):
        called["export"] = True
        raise AssertionError("should not reach Ghidra export if config validation fails first")

    monkeypatch.setattr(pipeline_module, "export_binary_to_binexport", fake_export)
    monkeypatch.setattr("shutil.which", lambda name: None)

    from orbis_diff.errors import ConfigurationError

    with pytest.raises(ConfigurationError):
        diff_binaries(old, new, cfg)  # validate_config defaults True

    assert called["export"] is False
