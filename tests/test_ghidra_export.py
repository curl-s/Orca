from __future__ import annotations

import subprocess

import pytest

from orbis_diff.config import OrbisDiffConfig
from orbis_diff.errors import GhidraExportError
from orbis_diff.ghidra_export import export_binary_to_binexport


def _cfg(tmp_path, headless, script_dir) -> OrbisDiffConfig:
    return OrbisDiffConfig(
        ghidra_headless=headless,
        binexport_script_path=script_dir,
        work_dir=tmp_path / "work",
        ghidra_analysis_timeout=5,
    )


def _setup(tmp_path):
    headless = tmp_path / "analyzeHeadless"
    headless.write_text("#!/bin/sh\n")
    headless.chmod(0o755)
    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()
    (script_dir / "BinExport.java").write_text("// fake")
    binary = tmp_path / "module.elf"
    binary.write_bytes(b"fake orbis binary")
    return headless, script_dir, binary


def test_successful_export_places_artifact_atomically(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        # Second invocation (-process ... -preScript) is the export step:
        # simulate BinExport.java writing its declared output file.
        if "-preScript" in cmd:
            out_path = cmd[-1]
            with open(out_path, "wb") as f:
                f.write(b"fake-binexport-content")
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = export_binary_to_binexport(binary, cfg)

    assert result.binexport_path.exists()
    assert result.binexport_path.read_bytes() == b"fake-binexport-content"
    # Stable, content-addressed location under work_dir/binexport/
    assert result.binexport_path.parent == cfg.work_dir / "binexport"


def test_import_failure_raises_with_stage_and_log(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        stdout.write(b"Ghidra analysis blew up\n")
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GhidraExportError, match="import/analysis"):
        export_binary_to_binexport(binary, cfg)


def test_export_step_failure_reported_distinctly_from_import(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        if "-preScript" in cmd:
            stdout.write(b"BinExport script threw an exception\n")
            return subprocess.CompletedProcess(cmd, returncode=1)
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GhidraExportError, match="BinExport export"):
        export_binary_to_binexport(binary, cfg)


def test_export_produces_no_file_raises_clear_error(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        # Exits 0 but never writes the declared output file -- simulates a
        # BinExport.java argument-parsing mismatch.
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GhidraExportError, match="no output"):
        export_binary_to_binexport(binary, cfg)


def test_export_produces_empty_file_raises_clear_error(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        if "-preScript" in cmd:
            out_path = cmd[-1]
            open(out_path, "wb").close()  # empty file
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GhidraExportError, match="empty file"):
        export_binary_to_binexport(binary, cfg)


def test_failed_run_does_not_leave_broken_artifact_at_stable_path(tmp_path, monkeypatch):
    headless, script_dir, binary = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    def fake_run(cmd, stdout, stderr, timeout=None):
        return subprocess.CompletedProcess(cmd, returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GhidraExportError):
        export_binary_to_binexport(binary, cfg)

    stable_dir = cfg.work_dir / "binexport"
    assert not stable_dir.exists() or list(stable_dir.iterdir()) == []


def test_different_binaries_same_filename_do_not_collide(tmp_path, monkeypatch):
    headless, script_dir, _ = _setup(tmp_path)
    cfg = _cfg(tmp_path, headless, script_dir)

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    binary_a = dir_a / "module.elf"
    binary_b = dir_b / "module.elf"
    binary_a.write_bytes(b"version A content")
    binary_b.write_bytes(b"version B content, longer and different")

    def fake_run(cmd, stdout, stderr, timeout=None):
        if "-preScript" in cmd:
            out_path = cmd[-1]
            with open(out_path, "wb") as f:
                f.write(b"exported-" + cmd[2].encode())  # project_name baked in
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result_a = export_binary_to_binexport(binary_a, cfg)
    result_b = export_binary_to_binexport(binary_b, cfg)

    assert result_a.binexport_path != result_b.binexport_path
    assert result_a.binexport_path.exists()
    assert result_b.binexport_path.exists()
