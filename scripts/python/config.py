"""Configuration for orbis-diff.

Everything here is a path or knob for an *external* tool (Ghidra, the
BinExport Ghidra script, and BinDiff's `differ` binary). orbis-diff does not
ship copies of these tools -- it locates and shells out to them.

All values can be overridden with environment variables so the tool works
across different install layouts without editing code. CLI flags (see
cli.py) take precedence over environment variables, which take precedence
over the defaults below.

CONFIDENCE NOTE (read this before wiring up your environment):
  - The `analyzeHeadless` invocation patterns and BinExport.java arguments
    below are CONFIRMED against Ghidra's and google/binexport's own docs
    as of this writing.
  - The exact GhidraOrbis loader class name is NOT hardcoded here: recent
    Ghidra extensions register themselves and are auto-selected by
    analyzeHeadless's format sniffing once the extension is installed, so
    we deliberately don't pass `-loader`. If your GhidraOrbis build needs
    an explicit loader, set GHIDRA_ORBIS_LOADER and pipeline.py will pass
    `-loader "$GHIDRA_ORBIS_LOADER"` on import. Treat that as a HYPOTHESIS
    to verify against the version of GhidraOrbis you have installed.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(name: str, default: str | None = None) -> Path | None:
    val = os.environ.get(name, default)
    return Path(val).expanduser() if val else None


@dataclass
class OrbisDiffConfig:
    # --- Ghidra ---
    ghidra_install_dir: Path | None = field(
        default_factory=lambda: _env_path("GHIDRA_INSTALL_DIR")
    )
    # support/analyzeHeadless (or analyzeHeadless.bat on Windows)
    ghidra_headless: Path | None = field(
        default_factory=lambda: _env_path("GHIDRA_HEADLESS")
    )
    # Optional explicit loader class/name for GhidraOrbis. Leave unset to
    # let Ghidra auto-detect via the installed extension. See module
    # docstring above.
    ghidra_orbis_loader: str | None = field(
        default_factory=lambda: os.environ.get("GHIDRA_ORBIS_LOADER")
    )
    ghidra_analysis_timeout: int = field(
        default_factory=lambda: int(os.environ.get("GHIDRA_ANALYSIS_TIMEOUT", "1800"))
    )

    # --- BinExport (Ghidra script) ---
    # Directory containing BinExport.java (from the google/binexport repo,
    # ghidra/scripts, or wherever you built/installed it) so it can be
    # passed to analyzeHeadless's -scriptPath.
    binexport_script_path: Path | None = field(
        default_factory=lambda: _env_path("BINEXPORT_SCRIPT_PATH")
    )
    binexport_script_name: str = field(
        default_factory=lambda: os.environ.get("BINEXPORT_SCRIPT_NAME", "BinExport.java")
    )

    # --- BinDiff ---
    # Directory or explicit binary. python-bindiff / the `differ` CLI look
    # for this via $PATH or $BINDIFF_PATH if not given here.
    bindiff_path: Path | None = field(
        default_factory=lambda: _env_path("BINDIFF_PATH")
    )

    # --- Working directories ---
    work_dir: Path = field(
        default_factory=lambda: _env_path("ORBIS_DIFF_WORKDIR", "/tmp/orbis-diff")
    )

    # --- Report thresholds ---
    # A matched function pair with similarity >= this value is treated as
    # "identical" and rolled into the matched-count summary rather than
    # printed individually under "Modified". Everything below is "Modified".
    identical_similarity_threshold: float = field(
        default_factory=lambda: float(os.environ.get("ORBIS_DIFF_IDENTICAL_THRESHOLD", "0.999"))
    )

    def resolve_headless(self) -> Path:
        if self.ghidra_headless and self.ghidra_headless.exists():
            return self.ghidra_headless
        if self.ghidra_install_dir:
            candidate = self.ghidra_install_dir / "support" / "analyzeHeadless"
            if candidate.exists():
                return candidate
        found = shutil.which("analyzeHeadless")
        if found:
            return Path(found)
        raise FileNotFoundError(
            "Could not locate Ghidra's analyzeHeadless. Set GHIDRA_INSTALL_DIR "
            "or GHIDRA_HEADLESS."
        )

    def resolve_binexport_script_path(self) -> Path:
        if self.binexport_script_path and self.binexport_script_path.exists():
            return self.binexport_script_path
        raise FileNotFoundError(
            "Could not locate the BinExport Ghidra script directory. Set "
            "BINEXPORT_SCRIPT_PATH to the directory containing "
            f"{self.binexport_script_name} (from the google/binexport project)."
        )

    def resolve_bindiff_env(self) -> dict:
        """Return env overrides to hand to subprocesses (for python-bindiff
        / the `differ` CLI, which honor BINDIFF_PATH)."""
        env = os.environ.copy()
        if self.bindiff_path:
            env["BINDIFF_PATH"] = str(self.bindiff_path)
        return env
