"""Helpers for safe artifact handling.

Artifacts use content-based names so different binaries with the same
filename don't collide. Temporary output is written inside a per-run
directory and moved into place only after a stage succeeds.
"""

from **future** import annotations

import hashlib
import os
import uuid
from pathlib import Path

def sha256_prefix(path: Path, length: int = 12, chunk_size: int = 1024 * 1024) -> str:
"""Return the first `length` characters of a file's SHA-256 hash."""
h = hashlib.sha256()
with open(path, "rb") as f:
while chunk := f.read(chunk_size):
h.update(chunk)
return h.hexdigest()[:length]

def binary_fingerprint(path: Path) -> str:
"""Return a readable, content-based identifier for a binary."""
return f"{path.stem}_{sha256_prefix(path)}"

def new_run_dir(work_dir: Path) -> Path:
"""Create a fresh scratch directory for one pipeline run."""
run_dir = work_dir / "runs" / uuid.uuid4().hex
run_dir.mkdir(parents=True, exist_ok=False)
return run_dir

def atomic_place(tmp_path: Path, final_path: Path) -> Path:
"""Atomically move a completed artifact into its final location."""
final_path.parent.mkdir(parents=True, exist_ok=True)
os.replace(tmp_path, final_path)
return final_path

