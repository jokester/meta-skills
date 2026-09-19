"""Find installable skills in this repo.

A skill is any directory containing SKILL.md.
OWN skills live under my/; EXTERNAL skills live inside git submodules
(paths read from .gitmodules, so uninitialized submodules are still listed
as collections — just with no skills in them yet).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import gitutil
from .model import Skill, SourceKind

# src/ihate_work/ai/meta_skills/discover.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

_PRUNE = {"__pycache__", "node_modules", "venv"}


def find_skill_dirs(root: Path) -> list[Path]:
    """All dirs under root containing SKILL.md (root itself included)."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE and not d.startswith(".")]
        if "SKILL.md" in filenames:
            found.append(Path(dirpath))
    return sorted(found)


@dataclass(frozen=True)
class Collection:
    """A group of skills: 'my', or one submodule."""

    name: str  # "my" or the submodule path, e.g. "obra/superpowers"
    path: Path
    source: SourceKind
    skills: tuple[Skill, ...]

    @property
    def initialized(self) -> bool:
        """False for a submodule that exists in .gitmodules but is not checked out."""
        return any(self.path.iterdir()) if self.path.is_dir() else False


def _scan(name: str, path: Path, source: SourceKind) -> Collection:
    skills = tuple(
        Skill(name=d.name, path=d, source=source, collection=name)
        for d in find_skill_dirs(path)
    )
    return Collection(name=name, path=path, source=source, skills=skills)


def discover(repo_root: Path = REPO_ROOT) -> list[Collection]:
    collections = [_scan("my", repo_root / "my", SourceKind.OWN)]
    for sub in gitutil.submodule_paths(repo_root):
        collections.append(_scan(sub, repo_root / sub, SourceKind.EXTERNAL))
    return collections


def all_skills(repo_root: Path = REPO_ROOT) -> list[Skill]:
    return [s for c in discover(repo_root) for s in c.skills]


def find_skill(query: str, repo_root: Path = REPO_ROOT) -> list[Skill]:
    """Skills matching query: an exact id, or a name/substring match."""
    skills = all_skills(repo_root)
    exact = [s for s in skills if s.id == query or s.name == query]
    return exact if exact else [s for s in skills if query in s.id]
