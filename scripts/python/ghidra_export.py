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
"""

from __future__ import annotations

import logging
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import OrbisDiffConfig

logger = logging.getLogger(__name__)


class GhidraExportError(RuntimeError):
    """Raised when Ghidra import/analysis/export fails."""


@dataclass
class ExportResult:
    binary_path: Path
    binexport_path: Path
    ghidra_log: Path


def _run(cmd: list[str], log_path: Path, timeout: int | None = None) -> None:
    logger.info("Running: %s", " ".join(str(c) for c in cmd))
    with open(log_path, "wb") as log_file:
        proc = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    if proc.returncode != 0:
        raise GhidraExportError(
            f"Command failed (exit {proc.returncode}): {' '.join(str(c) for c in cmd)}\n"
            f"See log: {log_path}"
        )


def import_and_analyze(binary: Path, project_dir: Path, project_name: str, cfg: OrbisDiffConfig) -> None:
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
        "-overwrite",  # project is kept around; export step re-opens it
    ]
    if cfg.ghidra_orbis_loader:
        cmd += ["-loader", cfg.ghidra_orbis_loader]

    log_path = project_dir / f"{project_name}.import.log"
    _run(cmd, log_path, timeout=cfg.ghidra_analysis_timeout + 300)


def export_binexport(
    binary: Path,
    project_dir: Path,
    project_name: str,
    out_file: Path,
    cfg: OrbisDiffConfig,
) -> ExportResult:
    """Re-open the analyzed program and export it with BinExport.java."""
    headless = cfg.resolve_headless()
    script_path = cfg.resolve_binexport_script_path()
    out_file.parent.mkdir(parents=True, exist_ok=True)

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
        str(out_file),
    ]

    log_path = project_dir / f"{project_name}.export.log"
    _run(cmd, log_path, timeout=cfg.ghidra_analysis_timeout + 300)

    if not out_file.exists():
        raise GhidraExportError(
            f"BinExport script ran but produced no output at {out_file}. "
            f"Check {log_path} -- this usually means BinExport.java's "
            "argument parsing differs from what's assumed here (see module "
            "docstring)."
        )
    return ExportResult(binary_path=binary, binexport_path=out_file, ghidra_log=log_path)


def export_binary_to_binexport(binary: Path, cfg: OrbisDiffConfig) -> ExportResult:
    """Full per-binary pipeline: import+analyze, then export. Returns the
    resulting .BinExport path."""
    binary = binary.resolve()
    run_id = uuid.uuid4().hex[:8]
    project_name = f"{binary.stem}_{run_id}"
    project_dir = cfg.work_dir / "ghidra_projects" / project_name
    out_file = cfg.work_dir / "binexport" / f"{binary.stem}_{run_id}.BinExport"

    import_and_analyze(binary, project_dir, project_name, cfg)
    return export_binexport(binary, project_dir, project_name, out_file, cfg)
