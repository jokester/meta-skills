"""Core vocabulary of the skill manager.

An install = (skill source, dest, method). See AGENTS.md for the full model.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path


class SourceKind(enum.Enum):
    OWN = "own"  # authored in this repo, under my/
    EXTERNAL = "external"  # vendored git submodule, pinned to a rev


class DestKind(enum.Enum):
    HOME = "home"  # a global agent skill dir, e.g. ~/.claude/skills
    REPO = "repo"  # a git repo (identified by .git at its root)
    DIR = "dir"  # any dir containing agent config dirs (.claude, .omp, ...)


class Method(enum.Enum):
    COPY = "copy"  # dest gets a permanent snapshot
    SYMLINK = "symlink"  # dest gets a pointer back into this repo
    CUSTOM = "custom"  # upstream has its own install story (see rewire.py)


@dataclass(frozen=True)
class Skill:
    """One installable skill: a directory containing SKILL.md."""

    name: str  # skill dir basename, e.g. "organize-workflow"
    path: Path  # absolute path of the skill dir
    source: SourceKind
    collection: str  # "my", or "<gh-user>/<repo>" for submodules

    @property
    def id(self) -> str:
        return f"{self.collection}/{self.name}"


@dataclass(frozen=True)
class Dest:
    """A resolved install destination: a root × a product convention."""

    kind: DestKind
    root: Path  # what the user pointed at (repo root for REPO, home for HOME)
    skills_dir: Path  # the dir skills actually get installed into
    product: str  # products.py key, e.g. "claude", "codex", "pi", "omp"


@dataclass(frozen=True)
class InstallPlan:
    """A validated (skill, dest, method) triple, ready to execute.

    warnings carry the "special rules" messages (e.g. REPO & SYMLINK) that
    the CLI must show before asking for confirmation.
    """

    skill: Skill
    dest: Dest
    method: Method
    warnings: tuple[str, ...] = ()

    @property
    def target(self) -> Path:
        return self.dest.skills_dir / self.skill.name
