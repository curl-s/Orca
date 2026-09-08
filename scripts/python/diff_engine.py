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
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import OrbisDiffConfig
from .models import DiffReport, FunctionMatchEntry, UnmatchedFunctionEntry

logger = logging.getLogger(__name__)


class DiffEngineError(RuntimeError):
    """Raised when BinDiff itself fails or python-bindiff can't parse its output."""


def run_bindiff(
    old_binexport: Path,
    new_binexport: Path,
    out_diff_file: Path,
    old_binary_path: str,
    new_binary_path: str,
    cfg: OrbisDiffConfig,
) -> DiffReport:
    try:
        from bindiff import BinDiff
        from bindiff.types import BindiffNotFound
    except ImportError as exc:  # pragma: no cover
        raise DiffEngineError(
            "python-bindiff is not installed. Run: pip install python-bindiff python-binexport"
        ) from exc

    import os

    for k, v in cfg.resolve_bindiff_env().items():
        os.environ.setdefault(k, v)

    try:
        BinDiff.assert_installation_ok()
    except BindiffNotFound as exc:
        raise DiffEngineError(
            "The BinDiff 'differ' binary was not found. Set BINDIFF_PATH or "
            "make sure it's on $PATH."
        ) from exc

    out_diff_file.parent.mkdir(parents=True, exist_ok=True)

    diff = BinDiff.from_binexport_files(
        str(old_binexport), str(new_binexport), str(out_diff_file), override=True
    )
    if diff is None:
        raise DiffEngineError("BinDiff produced no diff result (differ returned no output).")

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

    def _addr(fn) -> int:
        # python-binexport exposes this as `.addr`; fall back defensively
        # in case a pinned version differs.
        return getattr(fn, "addr", None) or getattr(fn, "address", None)

    removed = [
        UnmatchedFunctionEntry(name=fn.name or f"sub_{_addr(fn):x}", addr=_addr(fn))
        for fn in diff.primary_unmatched_function()
    ]
    added = [
        UnmatchedFunctionEntry(name=fn.name or f"sub_{_addr(fn):x}", addr=_addr(fn))
        for fn in diff.secondary_unmatched_function()
    ]

    return DiffReport(
        old_path=old_binary_path,
        new_path=new_binary_path,
        overall_similarity=diff.similarity,
        overall_confidence=diff.confidence,
        matched=matched,
        added=added,
        removed=removed,
    )
