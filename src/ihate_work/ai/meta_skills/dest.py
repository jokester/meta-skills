"""Classify and resolve install destinations (HOME / REPO / DIR)."""

from __future__ import annotations

from pathlib import Path

from . import gitutil
from .model import Dest, DestKind

# Global skill dirs agents look at, in preference order. HOME dests.
GLOBAL_SKILL_DIRS = [
    Path("~/.claude/skills"),
]

# Markers that make a plain dir an agent-configured dir. DIR dests.
AGENT_CONFIG_DIRS = [".claude", ".omp"]


def resolve(raw: str | Path) -> Dest:
    """Resolve a user-supplied path into a Dest, or raise ValueError.

    Priority: HOME (a known global skill dir) > REPO (inside a git repo)
    > DIR (contains an agent config dir).
    """
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"not a directory: {path}")

    for d in GLOBAL_SKILL_DIRS:
        d = d.expanduser()
        if path in (d, d.parent, Path.home()):
            return Dest(kind=DestKind.HOME, root=Path.home(), skills_dir=d)

    repo_root = gitutil.repo_root_of(path)
    if repo_root is not None:
        return Dest(
            kind=DestKind.REPO,
            root=repo_root,
            skills_dir=repo_root / ".claude" / "skills",
        )

    if any((path / marker).is_dir() for marker in AGENT_CONFIG_DIRS):
        return Dest(
            kind=DestKind.DIR, root=path, skills_dir=path / ".claude" / "skills"
        )

    raise ValueError(
        f"{path} is not a recognizable dest: not a global skill dir, "
        f"not inside a git repo, and has none of {AGENT_CONFIG_DIRS}"
    )
