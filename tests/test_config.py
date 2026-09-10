from __future__ import annotations

import pytest

from orbis_diff.config import OrbisDiffConfig
from orbis_diff.errors import ConfigurationError


def _bare_config(tmp_path, monkeypatch):
    """A config guaranteed to find nothing real, regardless of the host
    machine's PATH, so tests are hermetic."""
    monkeypatch.setattr("shutil.which", lambda name: None)
    cfg = OrbisDiffConfig(
        ghidra_install_dir=None,
        ghidra_headless=None,
        binexport_script_path=None,
        bindiff_path=None,
        work_dir=tmp_path / "work",
    )
    return cfg


def test_resolve_headless_missing_raises(tmp_path, monkeypatch):
    cfg = _bare_config(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        cfg.resolve_headless()


def test_resolve_headless_found_via_install_dir(tmp_path, monkeypatch):
    cfg = _bare_config(tmp_path, monkeypatch)
    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"
    assert cfg.resolve_headless() == headless


def test_resolve_binexport_script_path_missing_raises(tmp_path, monkeypatch):
    cfg = _bare_config(tmp_path, monkeypatch)
    with pytest.raises(FileNotFoundError):
        cfg.resolve_binexport_script_path()


def test_validate_reports_all_problems_at_once(tmp_path, monkeypatch):
    cfg = _bare_config(tmp_path, monkeypatch)
    # No Ghidra, no BinExport script, python-bindiff not importable (default
    # sys.modules -- not mocked in this test) -> validate() should raise
    # ConfigurationError listing multiple problems, not just the first.
    with pytest.raises(ConfigurationError) as excinfo:
        cfg.validate()
    msg = str(excinfo.value)
    assert "analyzeHeadless" in msg
    assert "BINEXPORT_SCRIPT_PATH" in msg


def test_validate_passes_with_everything_mocked(tmp_path, monkeypatch, fake_bindiff):
    cfg = _bare_config(tmp_path, monkeypatch)

    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"

    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()
    (script_dir / "BinExport.java").write_text("// fake")
    cfg.binexport_script_path = script_dir

    cfg.validate()  # should not raise


def test_validate_flags_missing_binexport_script_inside_configured_dir(tmp_path, monkeypatch, fake_bindiff):
    cfg = _bare_config(tmp_path, monkeypatch)

    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"

    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()  # exists, but BinExport.java is missing inside it
    cfg.binexport_script_path = script_dir

    with pytest.raises(ConfigurationError, match="BinExport.java was not found"):
        cfg.validate()


def test_validate_flags_bindiff_not_installed(tmp_path, monkeypatch):
    import sys

    # Simulate python-bindiff not being installed, regardless of whether
    # it's actually present in this test environment.
    monkeypatch.setitem(sys.modules, "bindiff", None)

    cfg = _bare_config(tmp_path, monkeypatch)
    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"
    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()
    (script_dir / "BinExport.java").write_text("// fake")
    cfg.binexport_script_path = script_dir

    with pytest.raises(ConfigurationError, match="python-bindiff is not installed"):
        cfg.validate()


def test_validate_flags_bindiff_differ_missing(tmp_path, monkeypatch, fake_bindiff):
    fake_bindiff["installation_ok"] = False
    cfg = _bare_config(tmp_path, monkeypatch)
    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"
    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()
    (script_dir / "BinExport.java").write_text("// fake")
    cfg.binexport_script_path = script_dir

    with pytest.raises(ConfigurationError, match="differ' binary was not found"):
        cfg.validate()


def test_validate_can_skip_bindiff_check(tmp_path, monkeypatch):
    cfg = _bare_config(tmp_path, monkeypatch)
    headless = tmp_path / "ghidra" / "support" / "analyzeHeadless"
    headless.parent.mkdir(parents=True)
    headless.write_text("#!/bin/sh\n")
    cfg.ghidra_install_dir = tmp_path / "ghidra"
    script_dir = tmp_path / "binexport_scripts"
    script_dir.mkdir()
    (script_dir / "BinExport.java").write_text("// fake")
    cfg.binexport_script_path = script_dir

    cfg.validate(require_bindiff=False)  # should not raise even without bindiff mocked
