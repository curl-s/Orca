"""Plain data models passed between pipeline stages.

Kept deliberately small and serialization-friendly (dataclasses only, no
tool-specific objects) so later phases (DB storage, HTML/web UI, etc.) can
consume this module without depending on Ghidra/BinExport/BinDiff types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _check_unit_interval(value: float, field_name: str) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{field_name} must be between 0 and 1, got {value!r}")


def _check_addr(value, field_name: str) -> None:
    if value is None or value < 0:
        raise ValueError(f"{field_name} must be a non-negative address, got {value!r}")


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

    def __post_init__(self) -> None:
        _check_addr(self.addr_old, "addr_old")
        _check_addr(self.addr_new, "addr_new")
        _check_unit_interval(self.similarity, "similarity")
        _check_unit_interval(self.confidence, "confidence")


@dataclass
class UnmatchedFunctionEntry:
    """A function present in only one of the two binaries."""

    name: str
    addr: int

    def __post_init__(self) -> None:
        _check_addr(self.addr, "addr")


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

    def __post_init__(self) -> None:
        _check_unit_interval(self.overall_similarity, "overall_similarity")
        _check_unit_interval(self.overall_confidence, "overall_confidence")

    @property
    def modified(self) -> list[FunctionMatchEntry]:
        return [m for m in self.matched if not m.is_identical]

    @property
    def identical_count(self) -> int:
        return sum(1 for m in self.matched if m.is_identical)
