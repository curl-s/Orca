"""Exception hierarchy for orbis-diff.

Expected errors carry the exit code used by the CLI.
"""

from __future__ import annotations


class OrbisDiffError(Exception):
    """Base class for all orbis-diff errors that should produce a clean
    CLI message + non-zero exit rather than a raw traceback."""

    exit_code = 1


class InputFileError(OrbisDiffError):
    """A given input path is missing, not a file, or unreadable."""

    exit_code = 3


class ConfigurationError(OrbisDiffError):
    """Required environment/config (Ghidra, BinExport script, BinDiff) is
    missing or invalid."""

    exit_code = 4


class GhidraExportError(OrbisDiffError):
    """Ghidra import, analysis, or BinExport export failed."""

    exit_code = 5


class DiffEngineError(OrbisDiffError):
    """BinDiff itself failed, or its output could not be parsed."""

    exit_code = 6
