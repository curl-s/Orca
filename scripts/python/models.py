"""Plain data models passed between pipeline stages.

Kept deliberately small and serialization-friendly (dataclasses only, no
tool-specific objects) so later phases (DB storage, HTML/web UI, etc.) can
consume this module without depending on Ghidra/BinExport/BinDiff types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FunctionMatchEntry:
    """One matched function pair from BinDiff."""

    name_old: str
    name_new: str
    addr_old: int
    addr_new: int
    similarity: float
    confidence: float
    is_identical: bool  # similarity >= config threshold


@dataclass
class UnmatchedFunctionEntry:
    """A function present in only one of the two binaries."""

    name: str
    addr: int


@dataclass
class DiffReport:
    """Full result of diffing two binaries, ready for reporting."""

    old_path: str
    new_path: str

    overall_similarity: float
    overall_confidence: float

    matched: list[FunctionMatchEntry] = field(default_factory=list)
    added: list[UnmatchedFunctionEntry] = field(default_factory=list)  # in new only
    removed: list[UnmatchedFunctionEntry] = field(default_factory=list)  # in old only

    @property
    def modified(self) -> list[FunctionMatchEntry]:
        return [m for m in self.matched if not m.is_identical]

    @property
    def identical_count(self) -> int:
        return sum(1 for m in self.matched if m.is_identical)
