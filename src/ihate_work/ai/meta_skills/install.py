"""Plan and execute installs, enforcing the special rules from AGENTS.md."""

from __future__ import annotations

import shutil
from pathlib import Path

from . import gitutil, manifest, rewire
from .discover import REPO_ROOT
from .model import Dest, DestKind, InstallPlan, Method, Skill, SourceKind


def source_rev(skill: Skill, repo_root: Path = REPO_ROOT) -> str | None:
    """The rev the skill's content is pinned to (for provenance/drift)."""
    if skill.source is SourceKind.EXTERNAL:
        return gitutil.submodule_rev(repo_root, skill.collection)
    return gitutil.head_rev(repo_root)


def plan(skill: Skill, dest: Dest, method: Method) -> InstallPlan:
    """Validate the triple and collect the warnings the user must see."""
    warnings: list[str] = []
    if dest.kind is DestKind.REPO and method is Method.SYMLINK:
        warnings.append(
            "REPO & SYMLINK: only suitable while *evaluating* skills — "
            "collaborators won't have the symlink targets. The links stay "
            "transient (gitignored via the skills dir's own .gitignore)."
        )
    if method is Method.CUSTOM:
        rev = source_rev(skill)
        if rewire.get(skill.collection, rev) is None:
            raise ValueError(
                f"no rewiring registered for ({skill.collection}, {rev}); "
                "study the upstream install script and add one in rewire.py"
            )
    return InstallPlan(skill=skill, dest=dest, method=method, warnings=tuple(warnings))


def execute(p: InstallPlan, *, force: bool = False) -> Path:
    """Perform the install; returns the target path."""
    target = p.target
    if target.exists() or target.is_symlink():
        if not force:
            raise FileExistsError(f"{target} already exists (use --force to replace)")
        _remove(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    if p.method is Method.COPY:
        shutil.copytree(p.skill.path, target, ignore=shutil.ignore_patterns(".git"))
    elif p.method is Method.SYMLINK:
        target.symlink_to(p.skill.path)
    elif p.method is Method.CUSTOM:
        rewiring = rewire.get(p.skill.collection, source_rev(p.skill))
        assert rewiring is not None  # plan() guarantees this
        rewiring(p.skill, p.dest)

    manifest.record(
        p.dest.skills_dir,
        skill_name=p.skill.name,
        skill_id=p.skill.id,
        method=p.method.value,
        source_rev=source_rev(p.skill),
    )
    # keep the manager's transient files (and symlinked skills) out of git
    if p.dest.kind in (DestKind.REPO, DestKind.DIR):
        names = (p.skill.name,) if p.method is Method.SYMLINK else ()
        gitutil.skills_gitignore_add(p.dest.skills_dir, names)
    return target


def uninstall(dest: Dest, skill_name: str) -> None:
    _remove(dest.skills_dir / skill_name)
    manifest.forget(dest.skills_dir, skill_name)
    gitutil.skills_gitignore_remove(dest.skills_dir, skill_name)


def _remove(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)
