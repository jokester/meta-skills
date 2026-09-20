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


def head_rev(repo_root: Path) -> str | None:
    """HEAD rev, or None when unknowable (no commits yet, git missing)."""
    try:
        return _git(repo_root, "rev-parse", "HEAD")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


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
    try:
        out = _git(repo_root, "ls-files", "-s", "--", sub_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    for line in out.splitlines():
        mode, sha, _rest = line.split(maxsplit=2)
        if mode == "160000":
            return sha
    return None


# The manager keeps its transient entries out of dest repos via a
# .gitignore it owns INSIDE the skills dir — never by editing the dest
# repo's own (tracked, human-owned) root .gitignore.
_MANAGED_HEADER = "# managed by meta-skills — transient entries, do not commit"
_BASELINE = [_MANAGED_HEADER, "/.gitignore"]


def skills_gitignore_add(skills_dir: Path, names: tuple[str, ...] = ()) -> None:
    """Ensure skills_dir/.gitignore ignores the manager's transient files.

    Baseline (always): the .gitignore itself and the manifest. Each name in
    names (symlinked skill dirs) gets its own line.
    """
    from .manifest import MANIFEST_NAME  # local import to avoid a cycle

    gi = skills_dir / ".gitignore"
    lines = gi.read_text().splitlines() if gi.is_file() else []
    if not lines:
        # MANIFEST glob also covers the .bad quarantine; staging/trash are
        # the install swap's short-lived intermediates
        lines = [*_BASELINE, f"/{MANIFEST_NAME}*", "/.staging-*", "/.trash-*"]
    for name in names:
        if f"/{name}" not in lines:
            lines.append(f"/{name}")
    skills_dir.mkdir(parents=True, exist_ok=True)
    gi.write_text("\n".join(lines) + "\n")


def skills_gitignore_remove(skills_dir: Path, name: str) -> None:
    gi = skills_dir / ".gitignore"
    if not gi.is_file():
        return
    lines = [ln for ln in gi.read_text().splitlines() if ln != f"/{name}"]
    gi.write_text("\n".join(lines) + "\n")
