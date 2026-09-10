"""orbis-diff CLI.

Usage:
    orbis-diff old.elf new.elf
    orbis-diff old.elf new.elf --verbose --show-identical
    orbis-diff old.elf new.elf --identical-threshold 0.95
    orbis-diff --check-env
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .config import OrbisDiffConfig
from .errors import OrbisDiffError
from .pipeline import diff_binaries
from .report import render_report


def _unit_interval(raw: str) -> float: Beyond binary diffing. Understand firmware evolution. 
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a number") from exc
    if not (0.0 <= value <= 1.0):
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orbis-diff",
        description="Minimal PS4/Orbis firmware binary diffing tool "
        "(Ghidra + GhidraOrbis + BinExport + BinDiff).",
        epilog=(
            "examples:\n"
            "  orbis-diff old.elf new.elf\n"
            "  orbis-diff old.elf new.elf --show-identical -v\n"
            "  orbis-diff --check-env                 # validate setup, no input files needed\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "old", type=Path, nargs="?", help="Path to the older decrypted Orbis ELF/module"
    )
    parser.add_argument(
        "new", type=Path, nargs="?", help="Path to the newer decrypted Orbis ELF/module"
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Validate Ghidra/BinExport/BinDiff configuration and exit. "
        "Does not require input files.",
    )
    parser.add_argument(
        "--show-identical",
        action="store_true",
        help="Also list functions that matched with (near-)100%% similarity",
    )
    parser.add_argument(
        "--identical-threshold",
        type=_unit_interval,
        default=None,
        metavar="0..1",
        help="Similarity at/above which a match is 'identical' rather than "
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
    parser.add_argument("--version", action="version", version=f"orbis-diff {__version__}")
    return parser


def _build_config(args: argparse.Namespace) -> OrbisDiffConfig:
    cfg = OrbisDiffConfig()
    if args.work_dir:
        cfg.work_dir = args.work_dir
    if args.identical_threshold is not None:
        cfg.identical_similarity_threshold = args.identical_threshold
    return cfg


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[%(levelname)s] %(message)s",
        force=True,  # reconfigure handlers on every call (matters for repeated
        # in-process invocations, e.g. tests, rather than relying on
        # basicConfig()'s no-op-if-already-configured default)
    )

    cfg = _build_config(args)

    if args.check_env:
        try:
            cfg.validate()
        except OrbisDiffError as exc:
            logging.error("%s", exc)
            return exc.exit_code
        print("orbis-diff: configuration OK "
              f"(work dir: {cfg.work_dir})")
        return 0

    if args.old is None or args.new is None:
        parser.error("the following arguments are required: old, new "
                     "(or pass --check-env to validate setup without input files)")
        return 2  # unreachable: parser.error() exits, but keeps type-checkers happy

    try:
        report = diff_binaries(args.old, args.new, cfg)
    except OrbisDiffError as exc:
        logging.error("%s", exc)
        if args.verbose:
            raise
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary for anything unexpected
        logging.error("orbis-diff failed unexpectedly: %s", exc)
        if args.verbose:
            raise
        logging.error("Re-run with -v for a full traceback.")
        return 1

    sys.stdout.write(render_report(report, show_identical=args.show_identical))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
