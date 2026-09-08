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
from pathlib import Path

from .config import OrbisDiffConfig
from .diff_engine import run_bindiff
from .ghidra_export import export_binary_to_binexport
from .models import DiffReport

logger = logging.getLogger(__name__)


def diff_binaries(old_binary: Path, new_binary: Path, cfg: OrbisDiffConfig) -> DiffReport:
    old_binary = Path(old_binary).resolve()
    new_binary = Path(new_binary).resolve()

    if not old_binary.exists():
        raise FileNotFoundError(old_binary)
    if not new_binary.exists():
        raise FileNotFoundError(new_binary)

    logger.info("Exporting old binary via Ghidra/GhidraOrbis/BinExport: %s", old_binary)
    old_export = export_binary_to_binexport(old_binary, cfg)

    logger.info("Exporting new binary via Ghidra/GhidraOrbis/BinExport: %s", new_binary)
    new_export = export_binary_to_binexport(new_binary, cfg)

    diff_out = cfg.work_dir / "bindiff" / f"{old_binary.stem}_vs_{new_binary.stem}.BinDiff"

    logger.info("Running BinDiff")
    report = run_bindiff(
        old_export.binexport_path,
        new_export.binexport_path,
        diff_out,
        str(old_binary),
        str(new_binary),
        cfg,
    )
    logger.info("BinDiff result stored at %s", diff_out)
    return report
