"""Drive Ghidra's headless analyzer to turn an Orbis binary into a
.BinExport file.

We do NOT reimplement any analysis here -- this module is a thin subprocess
wrapper around `analyzeHeadless`. Two invocations are used per binary,
mirroring the pattern documented by the google/binexport project:

  1. Import + auto-analyze the binary into a scratch Ghidra project.
     GhidraOrbis, once installed as a Ghidra extension, is auto-selected
     as the loader for Orbis ELF/module formats during this step.
  2. Re-open the already-analyzed program and run the BinExport.java
     post-script (with -noanalysis, since analysis already happened) to
     produce the .BinExport file BinDiff needs.

CONFIDENCE: step (1)'s command shape and step (2)'s
`-process ... -preScript BinExport.java <out> -noanalysis` shape are
CONFIRMED against Ghidra/binexport documentation. The exact set of
IDA-compatibility flags accepted after the output filename is a HYPOTHESIS
based on the binexport docs and may need adjusting for your BinExport
version -- run `analyzeHeadless -help` and inspect BinExport.java's
`getScriptArgsDescription`-equivalent if the export step fails.

Artifact handling: each invocation of `export_binary_to_binexport` gets its
own fresh scratch directory (artifacts.new_run_dir) for the Ghidra project
and logs, so a previous failed run can never leave stale/partial state that
a later run mistakes for a finished analysis. The final .BinExport is only
placed at its stable, content-addressed path (artifacts.binary_fingerprint)
via an atomic rename once the export has been verified to exist and be
non-empty -- so a crash mid-export never leaves a broken .BinExport where
BinDiff (or a you, yes you) might pick it up.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .artifacts import atomic_place, binary_fingerprint, new_run_dir
from .config import OrbisDiffConfig
from .errors import GhidraExportError

logger = logging.getLogger(__name__)

_LOG_TAIL_LINES = 40


@dataclass
class ExportResult:
    binary_path: Path
    binexport_path: Path
    ghidra_log_dir: Path


def _tail(log_path: Path, n: int = _LOG_TAIL_LINES) -> str:
    try:
        lines = log_path.read_text(errors="replace").splitlines()
    except OSError:
        return "(log file unavailable)"
    tail = lines[-n:]
    prefix = f"... ({len(lines) - n} earlier lines omitted) ...\n" if len(lines) > n else ""
    return prefix + "\n".join(tail)


def _run(cmd: list[str], log_path: Path, stage: str, timeout: int | None = None) -> None:
    logger.info("Running (%s): %s", stage, " ".join(str(c) for c in cmd))
    try:
        with open(log_path, "wb") as log_file:
            proc = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
    except FileNotFoundError as exc:
        raise GhidraExportError(
            f"Ghidra {stage} failed: could not execute '{cmd[0]}'. Is analyzeHeadless "
            f"path correct and executable? ({exc})"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise GhidraExportError(
            f"Ghidra {stage} timed out after {timeout}s. See log: {log_path}\n"
            f"Last output:\n{_tail(log_path)}"
        ) from exc

    if proc.returncode != 0:
        raise GhidraExportError(
            f"Ghidra {stage} failed (exit {proc.returncode}).\n"
            f"Command: {' '.join(str(c) for c in cmd)}\n"
            f"Full log: {log_path}\n"
            f"Last {_LOG_TAIL_LINES} lines:\n{_tail(log_path)}"
        )


def import_and_analyze(binary: Path, project_dir: Path, project_name: str, log_dir: Path, cfg: OrbisDiffConfig) -> None:
    """Import `binary` into a fresh Ghidra project and run Ghidra's default
    analysis. GhidraOrbis (installed as a Ghidra extension) is expected to
    be auto-selected as the loader for Orbis ELF/module input."""
    headless = cfg.resolve_headless()
    project_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(headless),
        str(project_dir),
        project_name,
        "-import",
        str(binary),
        "-analysisTimeoutPerFile",
        str(cfg.ghidra_analysis_timeout),
        "-overwrite",
    ]
    if cfg.ghidra_orbis_loader:
        cmd += ["-loader", cfg.ghidra_orbis_loader]

    log_path = log_dir / "import_analyze.log"
    _run(cmd, log_path, stage="import/analysis", timeout=cfg.ghidra_analysis_timeout + 300)


def export_binexport(
    binary: Path,
    project_dir: Path,
    project_name: str,
    scratch_out_file: Path,
    log_dir: Path,
    cfg: OrbisDiffConfig,
) -> Path:
    """Re-open the analyzed program and export it with BinExport.java into
    `scratch_out_file` (a path inside the run's own scratch dir -- the
    caller is responsible for atomically placing it at its stable,
    content-addressed location once this returns)."""
    headless = cfg.resolve_headless()
    script_path = cfg.resolve_binexport_script_path()
    scratch_out_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(headless),
        str(project_dir),
        project_name,
        "-process",
        binary.name,
        "-noanalysis",
        "-scriptPath",
        str(script_path),
        "-preScript",
        cfg.binexport_script_name,
        str(scratch_out_file),
    ]

    log_path = log_dir / "binexport.log"
    _run(cmd, log_path, stage="BinExport export", timeout=cfg.ghidra_analysis_timeout + 300)

    if not scratch_out_file.exists():
        raise GhidraExportError(
            f"BinExport script exited 0 but produced no output at {scratch_out_file}. "
            f"This usually means BinExport.java's argument parsing differs from what's "
            f"assumed here (see module docstring). Full log: {log_path}\n"
            f"Last {_LOG_TAIL_LINES} lines:\n{_tail(log_path)}"
        )
    if scratch_out_file.stat().st_size == 0:
        raise GhidraExportError(
            f"BinExport produced an empty file at {scratch_out_file}. Full log: {log_path}\n"
            f"Last {_LOG_TAIL_LINES} lines:\n{_tail(log_path)}"
        )
    return scratch_out_file


def export_binary_to_binexport(binary: Path, cfg: OrbisDiffConfig) -> ExportResult:
    """Full per-binary pipeline: import+analyze, then export.

    Uses a fresh scratch directory for the Ghidra project/logs on every
    call (never reused), and places the final .BinExport at a stable,
    content-addressed path only once it's verified good -- so a failure
    partway through never leaves a broken or misleading artifact behind
    at the stable path, and different binaries can never clobber each
    other's output even if they share a filename.
    """
    binary = binary.resolve()
    fingerprint = binary_fingerprint(binary)
    run_dir = new_run_dir(cfg.work_dir)

    project_dir = run_dir / "ghidra_project"
    project_name = fingerprint
    scratch_out_file = run_dir / f"{fingerprint}.BinExport"
    final_out_file = cfg.work_dir / "binexport" / f"{fingerprint}.BinExport"

    import_and_analyze(binary, project_dir, project_name, run_dir, cfg)
    export_binexport(binary, project_dir, project_name, scratch_out_file, run_dir, cfg)

    final_path = atomic_place(scratch_out_file, final_out_file)
    logger.info("BinExport artifact for %s ready at %s", binary, final_path)
    return ExportResult(binary_path=binary, binexport_path=final_path, ghidra_log_dir=run_dir)
