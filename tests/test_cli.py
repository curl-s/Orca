from __future__ import annotations

import pytest

import orbis_diff.cli as cli_module
from orbis_diff.errors import ConfigurationError, DiffEngineError, GhidraExportError, InputFileError


def test_help_exits_zero_and_prints_usage(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "orbis-diff" in out
    assert "old" in out and "new" in out


def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main(["--version"])
    assert excinfo.value.code == 0


def test_missing_positional_args_exits_with_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main([])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "required" in err.lower()


def test_missing_input_file_gives_clear_error_and_nonzero_exit(tmp_path, capsys):
    new = tmp_path / "new.elf"
    new.write_bytes(b"data")
    rc = cli_module.main([str(tmp_path / "missing_old.elf"), str(new)])
    assert rc == InputFileError.exit_code
    assert rc != 0
    err = capsys.readouterr().err
    assert "old binary not found" in err


def test_invalid_identical_threshold_rejected_by_argparse(tmp_path, capsys):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"1")
    new.write_bytes(b"2")
    with pytest.raises(SystemExit) as excinfo:
        cli_module.main([str(old), str(new), "--identical-threshold", "3.0"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "between 0 and 1" in err


def test_check_env_reports_configuration_error_with_correct_exit_code(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("shutil.which", lambda name: None)
    rc = cli_module.main(["--check-env", "--work-dir", str(tmp_path)])
    assert rc == ConfigurationError.exit_code
    err = capsys.readouterr().err
    assert "analyzeHeadless" in err


def test_check_env_success_does_not_require_input_files(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("orbis_diff.config.OrbisDiffConfig.validate", lambda self, **kw: None)
    rc = cli_module.main(["--check-env", "--work-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "configuration OK" in out


@pytest.mark.parametrize(
    "error_cls",
    [InputFileError, ConfigurationError, GhidraExportError, DiffEngineError],
)
def test_pipeline_errors_map_to_declared_exit_codes(tmp_path, monkeypatch, capsys, error_cls):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"1")
    new.write_bytes(b"2")

    def boom(*args, **kwargs):
        raise error_cls("simulated failure")

    monkeypatch.setattr(cli_module, "diff_binaries", boom)

    rc = cli_module.main([str(old), str(new)])
    assert rc == error_cls.exit_code
    assert rc != 0
    err = capsys.readouterr().err
    assert "simulated failure" in err


def test_unexpected_exception_returns_generic_exit_code_one(tmp_path, monkeypatch, capsys):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"1")
    new.write_bytes(b"2")

    def boom(*args, **kwargs):
        raise RuntimeError("totally unexpected")

    monkeypatch.setattr(cli_module, "diff_binaries", boom)

    rc = cli_module.main([str(old), str(new)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unexpectedly" in err


def test_verbose_reraises_full_traceback(tmp_path, monkeypatch):
    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"1")
    new.write_bytes(b"2")

    def boom(*args, **kwargs):
        raise GhidraExportError("boom with details")

    monkeypatch.setattr(cli_module, "diff_binaries", boom)

    with pytest.raises(GhidraExportError, match="boom with details"):
        cli_module.main([str(old), str(new), "-v"])


def test_successful_run_prints_report_and_returns_zero(tmp_path, monkeypatch, capsys):
    from orbis_diff.models import DiffReport, FunctionMatchEntry

    old = tmp_path / "old.elf"
    new = tmp_path / "new.elf"
    old.write_bytes(b"1")
    new.write_bytes(b"2")

    report = DiffReport(
        old_path=str(old),
        new_path=str(new),
        overall_similarity=0.9,
        overall_confidence=0.9,
        matched=[FunctionMatchEntry("sceFoo", "sceFoo", 0x1, 0x2, 0.5, 0.5, is_identical=False)],
    )

    monkeypatch.setattr(cli_module, "diff_binaries", lambda *a, **k: report)

    rc = cli_module.main([str(old), str(new)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "sceFoo" in out
    assert "Modified:" in out
