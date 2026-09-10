"""Run BinDiff on two .BinExport files and normalize the result.

This module does not talk to BinDiff's `differ` binary or parse its SQLite
output directly -- it delegates both to `python-bindiff`
(https://github.com/quarkslab/python-bindiff), which already wraps the
`differ` CLI and knows the .BinDiff schema, including how to compute
per-binary unmatched (added/removed) functions by cross-referencing the
.BinExport data. This keeps orbis-diff from reimplementing any of that.

Install with: pip install python-bindiff python-binexport

CONFIDENCE: the API surface used here (BinDiff.from_binexport_files,
iter_function_matches, primary_unmatched_function,
secondary_unmatched_function) is CONFIRMED against python-bindiff's
published API docs as of this writing. Pin a known-good version in
requirements.txt if you hit breaking API changes upstream.

Artifact handling: BinDiff writes its .BinDiff result to a scratch path
inside the run's own directory; only once python-bindiff has successfully
parsed it back out do we atomically place it at its stable path
(work_dir/bindiff/...). A `differ` crash or a malformed result therefore
never leaves a broken .BinDiff file at the stable, "looks finished"
location.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from .artifacts import atomic_place
from .config import OrbisDiffConfig
from .errors import DiffEngineError
from .models import DiffReport, FunctionMatchEntry, UnmatchedFunctionEntry

logger = logging.getLogger(__name__)


def _addr(fn) -> int | None:
    # python-binexport exposes this as `.addr`; fall back defensively in
    # case a pinned version differs.
    return getattr(fn, "addr", None) or getattr(fn, "address", None)


def _unmatched_name(fn) -> str:
    addr = _addr(fn)
    return fn.name or (f"sub_{addr:x}" if addr is not None else "sub_unknown")


def run_bindiff(
    old_binexport: Path,
    new_binexport: Path,
    scratch_diff_file: Path,
    final_diff_file: Path,
    old_binary_path: str,
    new_binary_path: str,
    cfg: OrbisDiffConfig,
) -> DiffReport:
    try:
        from bindiff import BinDiff
    except ImportError as exc:
        raise DiffEngineError(
            "python-bindiff is not installed. Run: pip install python-bindiff python-binexport"
        ) from exc

    for missing, path in (("old", old_binexport), ("new", new_binexport)):
        if not path.exists():
            raise DiffEngineError(f"{missing} .BinExport file is missing: {path}")

    for k, v in cfg.resolve_bindiff_env().items():
        os.environ.setdefault(k, v)

    try:
        BinDiff.assert_installation_ok()
    except Exception as exc:  # noqa: BLE001 - exact exception type is an external API detail
        raise DiffEngineError(
            "The BinDiff 'differ' binary was not found or is not working "
            f"({exc}). Set BINDIFF_PATH or make sure it's on $PATH."
        ) from exc

    scratch_diff_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        diff = BinDiff.from_binexport_files(
            str(old_binexport), str(new_binexport), str(scratch_diff_file), override=True
        )
    except Exception as exc:  # noqa: BLE001 - wrap any differ/parsing failure with context
        raise DiffEngineError(
            f"BinDiff failed comparing {old_binexport.name} vs {new_binexport.name}: {exc}"
        ) from exc

    if diff is None:
        raise DiffEngineError(
            f"BinDiff produced no diff result for {old_binexport.name} vs "
            f"{new_binexport.name} (differ returned no output)."
        )

    try:
        matched: list[FunctionMatchEntry] = []
        for fn_old, fn_new, match in diff.iter_function_matches():
            matched.append(
                FunctionMatchEntry(
                    name_old=fn_old.name or f"sub_{match.address1:x}",
                    name_new=fn_new.name or f"sub_{match.address2:x}",
                    addr_old=match.address1,
                    addr_new=match.address2,
                    similarity=match.similarity,
                    confidence=match.confidence,
                    is_identical=match.similarity >= cfg.identical_similarity_threshold,
                )
            )

        removed = [
            UnmatchedFunctionEntry(name=_unmatched_name(fn), addr=_addr(fn))
            for fn in diff.primary_unmatched_function()
        ]
        added = [
            UnmatchedFunctionEntry(name=_unmatched_name(fn), addr=_addr(fn))
            for fn in diff.secondary_unmatched_function()
        ]

        report = DiffReport(
            old_path=old_binary_path,
            new_path=new_binary_path,
            overall_similarity=diff.similarity,
            overall_confidence=diff.confidence,
            matched=matched,
            added=added,
            removed=removed,
        )
    except DiffEngineError:
        raise
    except Exception as exc:  # noqa: BLE001 - malformed/unexpected BinDiff result shape
        raise DiffEngineError(
            f"BinDiff produced a result but it could not be parsed into a report: {exc}"
        ) from exc

    # Only now, with a fully-parsed report in hand, is the .BinDiff file
    # promoted to its stable location.
    if scratch_diff_file.exists():
        atomic_place(scratch_diff_file, final_diff_file)
        logger.info("BinDiff artifact ready at %s", final_diff_file)
    else:
        logger.warning(
            "BinDiff parsed a result but no .BinDiff file was found at %s to preserve",
            scratch_diff_file,
        )

    return report
