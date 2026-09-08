"""orbis-diff: minimal PS4/Orbis firmware binary diffing tool.

Pipeline:
    Orbis ELF/module -> Ghidra (+GhidraOrbis loader) -> BinExport -> BinDiff -> report

This package is deliberately thin. It does not reimplement disassembly,
function matching, or similarity scoring -- all of that is delegated to
Ghidra, BinExport, and BinDiff. This package only orchestrates those tools
and formats their output.
"""

__version__ = "0.1.0"
