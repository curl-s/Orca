"""orbis-diff CLI.

Usage:
    orbis-diff old.elf new.elf
    orbis-diff old.elf new.elf --verbose --show-identical
    orbis-diff old.elf new.elf --identical-threshold 0.95
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import OrbisDiffConfig
from .pipeline import diff_binaries
from .report import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orbis-diff",
        description="Minimal PS4/Orbis firmware binary diffing tool "
        "(Ghidra + GhidraOrbis + BinExport + BinDiff).",
    )
    parser.add_argument("old", type=Path, help="Path to the older decrypted Orbis ELF/module")
    parser.add_argument("new", type=Path, help="Path to the newer decrypted Orbis ELF/module")
    parser.add_argument(
        "--show-identical",
        action="store_true",
        help="Also list functions that matched with (near-)100%% similarity",
    )
    parser.add_argument(
        "--identical-threshold",
        type=float,
        default=None,
        help="Similarity (0..1) at/above which a match is 'identical' rather than "
        "'modified'. Default: 0.999 (or $ORBIS_DIFF_IDENTICAL_THRESHOLD)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Scratch directory for Ghidra projects / .BinExport / .BinDiff files. "
        "Default: /tmp/orbis-diff (or $ORBIS_DIFF_WORKDIR)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
    )

    cfg = OrbisDiffConfig()
    if args.work_dir:
        cfg.work_dir = args.work_dir
    if args.identical_threshold is not None:
        cfg.identical_similarity_threshold = args.identical_threshold

    try:
        report = diff_binaries(args.old, args.new, cfg)
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary
        logging.error("orbis-diff failed: %s", exc)
        if args.verbose:
            raise
        return 1

    sys.stdout.write(render_report(report, show_identical=args.show_identical))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
