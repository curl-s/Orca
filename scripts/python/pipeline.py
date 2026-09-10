"""Wire the stages together: Orbis binary pair -> DiffReport.

    old.elf ---\\                                    /--- report
                Ghidra+GhidraOrbis -> BinExport -> BinDiff
    new.elf ---/                                    \\--- .BinDiff file (kept)

Each stage is independently swappable (see ghidra_export.py, diff_engine.py)
so later phases can slot in e.g. batch processing over many modules without
touching this file's shape.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .artifacts import binary_fingerprint, new_run_dir
from .config import OrbisDiffConfig
from .diff_engine import run_bindiff
from .errors import InputFileError
from .ghidra_export import export_binary_to_binexport
from .models import DiffReport

logger = logging.getLogger(__name__)


def _validate_input_file(path: Path, label: str) -> Path:
    path = Path(path)
    if not path.exists():
        raise InputFileError(f"{label} binary not found: {path}")
    if not path.is_file():
        raise InputFileError(f"{label} binary is not a regular file: {path}")
    if not os.access(path, os.R_OK):
        raise InputFileError(f"{label} binary is not readable (check permissions): {path}")
    if path.stat().st_size == 0:
        raise InputFileError(f"{label} binary is empty: {path}")
    return path.resolve()


def diff_binaries(
    old_binary: Path,
    new_binary: Path,
    cfg: OrbisDiffConfig,
    validate_config: bool = True,
) -> DiffReport:
    old_binary = _validate_input_file(old_binary, "old")
    new_binary = _validate_input_file(new_binary, "new")

    if validate_config:
        # Fail fast on missing Ghidra/BinExport/BinDiff *before* spending
        # minutes on analysis, with every problem listed at once.
        cfg.validate()

    logger.info("Exporting old binary via Ghidra/GhidraOrbis/BinExport: %s", old_binary)
    old_export = export_binary_to_binexport(old_binary, cfg)

    logger.info("Exporting new binary via Ghidra/GhidraOrbis/BinExport: %s", new_binary)
    new_export = export_binary_to_binexport(new_binary, cfg)

    old_fp = binary_fingerprint(old_binary)
    new_fp = binary_fingerprint(new_binary)
    diff_run_dir = new_run_dir(cfg.work_dir)
    scratch_diff_file = diff_run_dir / f"{old_fp}_vs_{new_fp}.BinDiff"
    final_diff_file = cfg.work_dir / "bindiff" / f"{old_fp}_vs_{new_fp}.BinDiff"

    logger.info("Running BinDiff")
    report = run_bindiff(
        old_export.binexport_path,
        new_export.binexport_path,
        scratch_diff_file,
        final_diff_file,
        str(old_binary),
        str(new_binary),
        cfg,
    )
    return report
