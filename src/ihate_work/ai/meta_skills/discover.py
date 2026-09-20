"""Find installable skills in this repo.

A skill is any directory containing SKILL.md.
OWN skills live under my/; EXTERNAL skills live inside git submodules
(paths read from .gitmodules, so uninitialized submodules are still listed
as collections — just with no skills in them yet); REMOTE skills live under
build/, derived by `./cli extract` from an upstream we never vendor (see
recipes.py). A collection that has nothing to offer yet never vanishes —
it carries the hint that says how to populate it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import extract, gitutil, recipes
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

    name: str  # "my", a submodule path, or a recipe's collection name
    path: Path
    source: SourceKind
    skills: tuple[Skill, ...]
    hint: str | None = None  # why it is empty / stale, and what to run

    @property
    def initialized(self) -> bool:
        """False for a submodule that exists in .gitmodules but is not checked out."""
        return any(self.path.iterdir()) if self.path.is_dir() else False


def _scan(
    name: str, path: Path, source: SourceKind, hint: str | None = None
) -> Collection:
    skills = tuple(
        Skill(name=d.name, path=d, source=source, collection=name)
        for d in find_skill_dirs(path)
    )
    return Collection(name=name, path=path, source=source, skills=skills, hint=hint)


def _remote(recipe: recipes.Recipe, repo_root: Path) -> Collection:
    """A recipe's collection, served from its extract under build/."""
    path = extract.build_dir(repo_root, recipe.collection)
    state = extract.state_of(repo_root, recipe.collection)
    if not state:
        hint = f"not extracted — run: ./cli extract {recipe.collection}"
    elif state.get("rev") != recipe.rev:
        hint = (
            f"extract is stale (built at {str(state.get('rev'))[:7]}, recipe "
            f"pins {recipe.rev[:7]}) — re-run: ./cli extract {recipe.collection}"
        )
    else:
        hint = None
    return _scan(recipe.collection, path, SourceKind.REMOTE, hint)


def discover(repo_root: Path = REPO_ROOT) -> list[Collection]:
    collections = [_scan("my", repo_root / "my", SourceKind.OWN)]
    for sub in gitutil.submodule_paths(repo_root):
        hint = None
        if not (repo_root / sub).is_dir() or not any((repo_root / sub).iterdir()):
            hint = f"not initialized — run: git submodule update --init {sub}"
        collections.append(_scan(sub, repo_root / sub, SourceKind.EXTERNAL, hint))
    for recipe in recipes.all_recipes():
        collections.append(_remote(recipe, repo_root))
    return collections


def all_skills(repo_root: Path = REPO_ROOT) -> list[Skill]:
    return [s for c in discover(repo_root) for s in c.skills]


def find_skill(query: str, repo_root: Path = REPO_ROOT) -> list[Skill]:
    """Skills matching query: an exact id, or a name/substring match."""
    skills = all_skills(repo_root)
    exact = [s for s in skills if s.id == query or s.name == query]
    return exact if exact else [s for s in skills if query in s.id]
