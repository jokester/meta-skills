"""Small git helpers. All shell out to git; no dependency on GitPython."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def repo_root_of(path: Path) -> Path | None:
    """The enclosing git repo's root, or None if path is not in a repo."""
    p = path if path.is_dir() else path.parent
    try:
        return Path(_git(p, "rev-parse", "--show-toplevel"))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def head_rev(repo_root: Path) -> str:
    return _git(repo_root, "rev-parse", "HEAD")


def submodule_paths(repo_root: Path) -> list[str]:
    """Submodule paths as recorded in .gitmodules, e.g. 'obra/superpowers'."""
    if not (repo_root / ".gitmodules").is_file():
        return []
    out = _git(
        repo_root,
        "config",
        "-f",
        ".gitmodules",
        "--get-regexp",
        r"submodule\..*\.path",
    )
    return [line.split(maxsplit=1)[1] for line in out.splitlines()]


def submodule_rev(repo_root: Path, sub_path: str) -> str | None:
    """The rev a submodule is pinned to (works even when uninitialized)."""
    out = _git(repo_root, "ls-files", "-s", "--", sub_path)
    for line in out.splitlines():
        mode, sha, _rest = line.split(maxsplit=2)
        if mode == "160000":
            return sha
    return None


def ensure_gitignored(repo_root: Path, rel_path: str) -> bool:
    """Make sure rel_path is ignored in repo_root; append to .gitignore if not.

    Returns True if .gitignore was modified.
    """
    try:
        _git(repo_root, "check-ignore", "-q", rel_path)
        return False  # already ignored
    except subprocess.CalledProcessError:
        pass
    gitignore = repo_root / ".gitignore"
    existing = gitignore.read_text() if gitignore.is_file() else ""
    line = f"/{rel_path}"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    gitignore.write_text(existing + line + "\n")
    return True
