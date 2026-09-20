"""Filesystem primitives shared by the mutating code paths.

Both installs and extractions land content by stage-then-swap: build the
whole thing somewhere else, then move it into place in one rename. A crash
mid-build can never leave a half-written skill (or a half-written extract)
at the target.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def remove(target: Path) -> None:
    """Delete a file, symlink or dir; a missing path is not an error."""
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def swap(staged: Path, target: Path) -> None:
    """Move fully-staged content onto target; restore the old one on failure."""
    trash = None
    if target.exists() or target.is_symlink():
        trash = target.parent / f".trash-{target.name}"
        remove(trash)
        target.rename(trash)
    try:
        staged.rename(target)
    except OSError:
        if trash is not None:
            trash.rename(target)
        raise
    if trash is not None:
        remove(trash)
