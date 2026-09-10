"""Shared fixtures.

None of these tests require Ghidra, GhidraOrbis, BinExport, or a real
BinDiff `differ` binary to be installed. `fake_bindiff` replaces the
`bindiff` package (which diff_engine.py imports lazily, inside the
function) with an in-memory fake, so diff_engine/config's behavior against
BinDiff's public API surface can be tested without the real tool.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def make_binary(tmp_path):
    """Factory fixture: create a small fake binary file and return its path."""

    def _make(name: str = "binary.elf", content: bytes = b"\x7fELF fake orbis binary content") -> Path:
        p = tmp_path / name
        p.write_bytes(content)
        return p

    return _make


class FakeFunction:
    """Stand-in for python-binexport's FunctionBinExport."""

    def __init__(self, name: str | None, addr: int):
        self.name = name
        self.addr = addr


class FakeMatch:
    """Stand-in for a python-bindiff function match record."""

    def __init__(self, address1: int, address2: int, similarity: float, confidence: float):
        self.address1 = address1
        self.address2 = address2
        self.similarity = similarity
        self.confidence = confidence


@pytest.fixture
def fake_bindiff(monkeypatch):
    """Install a fake `bindiff` module into sys.modules for the duration of
    the test and return a mutable `state` dict the test configures before
    exercising orbis_diff.diff_engine / orbis_diff.config.

    state keys:
      matches           -- list[(FakeFunction, FakeFunction, FakeMatch)]
      removed           -- list[FakeFunction]  (primary-only / "removed")
      added             -- list[FakeFunction]  (secondary-only / "added")
      similarity        -- float, overall
      confidence        -- float, overall
      installation_ok   -- bool, controls assert_installation_ok()
      raise_on_diff     -- Exception instance to raise from from_binexport_files, or None
      write_output_file -- bool, whether from_binexport_files writes the scratch .BinDiff
    """
    state = {
        "matches": [],
        "removed": [],
        "added": [],
        "similarity": 1.0,
        "confidence": 1.0,
        "installation_ok": True,
        "raise_on_diff": None,
        "write_output_file": True,
        "FakeFunction": FakeFunction,
        "FakeMatch": FakeMatch,
    }

    class FakeBinDiffInstance:
        def iter_function_matches(self):
            return iter(state["matches"])

        def primary_unmatched_function(self):
            return iter(state["removed"])

        def secondary_unmatched_function(self):
            return iter(state["added"])

        @property
        def similarity(self):
            return state["similarity"]

        @property
        def confidence(self):
            return state["confidence"]

    class FakeBindiffNotFound(Exception):
        pass

    class FakeBinDiff:
        @classmethod
        def assert_installation_ok(cls):
            if not state["installation_ok"]:
                raise FakeBindiffNotFound("fake: differ binary not found")

        @classmethod
        def from_binexport_files(cls, old, new, out, override=True):
            if state["raise_on_diff"] is not None:
                raise state["raise_on_diff"]
            if state["write_output_file"]:
                Path(out).write_bytes(b"fake-bindiff-sqlite-content")
            return FakeBinDiffInstance()

    fake_module = types.ModuleType("bindiff")
    fake_module.BinDiff = FakeBinDiff

    fake_types_module = types.ModuleType("bindiff.types")
    fake_types_module.BindiffNotFound = FakeBindiffNotFound
    fake_module.types = fake_types_module

    monkeypatch.setitem(sys.modules, "bindiff", fake_module)
    monkeypatch.setitem(sys.modules, "bindiff.types", fake_types_module)

    return state
