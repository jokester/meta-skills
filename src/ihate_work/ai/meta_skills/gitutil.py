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


def in_git_worktree(path: Path) -> bool:
    """True when path sits inside a git worktree (checked structurally)."""
    return any((q / ".git").exists() for q in (path, *path.parents))


# The manager keeps its transient entries out of dest repos via a
# .gitignore it owns INSIDE the skills dir (<repo>/.claude/skills/.gitignore
# etc.) — never by editing the dest repo's own (tracked, human-owned) root
# .gitignore. All manager lines live inside one START/END-delimited section,
# so adds/removes are surgical and anything a human writes outside the
# section is preserved verbatim. Only written when the dest is in a git repo.
SECTION_START = "# added by jokester/meta-skills START"
SECTION_END = "# added by jokester/meta-skills END"


def _baseline() -> list[str]:
    from .manifest import MANIFEST_NAME  # local import to avoid a cycle

    # MANIFEST glob also covers the .bad quarantine; staging/trash are the
    # install swap's short-lived intermediates
    return ["/.gitignore", f"/{MANIFEST_NAME}*", "/.staging-*", "/.trash-*"]


def _split_section(text: str) -> tuple[list[str], list[str], list[str]]:
    """(lines before, entries inside, lines after) the managed section."""
    lines = text.splitlines()
    if SECTION_START in lines:
        i = lines.index(SECTION_START)
        if SECTION_END in lines[i:]:
            j = lines.index(SECTION_END, i)
            return lines[:i], lines[i + 1 : j], lines[j + 1 :]
    return lines, [], []


def _write_section(
    gi: Path, before: list[str], entries: list[str], after: list[str]
) -> None:
    lines = [*before, SECTION_START, *entries, SECTION_END, *after]
    gi.write_text("\n".join(lines) + "\n")


def skills_gitignore_add(skills_dir: Path, names: tuple[str, ...] = ()) -> None:
    """Ensure the managed section ignores the manager's transient files.

    Baseline (always): the .gitignore itself, the manifest, and the
    stage/swap intermediates. Each name in names (symlinked skill dirs)
    gets its own line. Content outside the section is untouched.
    """
    gi = skills_dir / ".gitignore"
    before, entries, after = _split_section(gi.read_text() if gi.is_file() else "")
    for line in (*_baseline(), *(f"/{n}" for n in names)):
        if line not in entries:
            entries.append(line)
    skills_dir.mkdir(parents=True, exist_ok=True)
    _write_section(gi, before, entries, after)


def skills_gitignore_remove(skills_dir: Path, name: str) -> None:
    """Drop one entry from the managed section; never touches other lines."""
    gi = skills_dir / ".gitignore"
    if not gi.is_file():
        return
    before, entries, after = _split_section(gi.read_text())
    if f"/{name}" not in entries:
        return
    entries.remove(f"/{name}")
    _write_section(gi, before, entries, after)
