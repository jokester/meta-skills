"""Plan and execute installs, enforcing the special rules from docs/SPEC.md.

Atomicity contract: no mutable operation happens unless preflight() says
the whole install will succeed, and content lands via stage-then-swap — a
failure can never leave a half-written skill at the target.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from . import extract, fsutil, gitutil, manifest, recipes, rewire
from .discover import REPO_ROOT
from .errors import MetaSkillsError, TargetExists
from .model import Dest, DestKind, InstallPlan, Method, Skill, SourceKind


def source_rev(skill: Skill, repo_root: Path = REPO_ROOT) -> str | None:
    """The rev the skill's content is pinned to; None = provenance unknown."""
    if skill.source is SourceKind.EXTERNAL:
        return gitutil.submodule_rev(repo_root, skill.collection)
    if skill.source is SourceKind.REMOTE:
        # not vendored: the pin lives in the recipe that produced the extract
        recipe = recipes.get(skill.collection)
        return recipe.rev if recipe else None
    return gitutil.head_rev(repo_root)


def plan(skill: Skill, dest: Dest, method: Method) -> InstallPlan:
    """Validate the triple and collect the warnings the user must see."""
    warnings: list[str] = []
    if skill.source is SourceKind.REMOTE:
        recipe = recipes.get(skill.collection)
        # the rev we would record comes from the recipe, so installing an
        # extract built at an older pin would file the content under a rev
        # it was never built from — a provenance lie, not a stale warning
        if recipe is not None and extract.is_stale(REPO_ROOT, recipe):
            raise MetaSkillsError(
                f"{skill.collection} was extracted at an older pin — "
                f"re-run: ./cli extract {skill.collection}"
            )
    if dest.kind is DestKind.REPO and method is Method.SYMLINK:
        warnings.append(
            "REPO & SYMLINK: only suitable while *evaluating* skills — "
            "collaborators won't have the symlink targets. The links stay "
            "transient (gitignored via the skills dir's own .gitignore)."
        )
    if method is Method.CUSTOM:
        rev = source_rev(skill)
        if rewire.get(skill.collection, rev) is None:
            raise MetaSkillsError(
                f"no rewiring registered for ({skill.collection}, {rev}); "
                "study the upstream install script and add one in rewire.py"
            )
    return InstallPlan(skill=skill, dest=dest, method=method, warnings=tuple(warnings))


def preflight(p: InstallPlan, *, force: bool = False) -> None:
    """Raise unless the install is confidently going to succeed.

    Called before ANY mutation — both by the CLI (over the whole batch,
    before confirming) and by execute() itself.
    """
    if not (p.skill.path / "SKILL.md").is_file():
        raise MetaSkillsError(f"source vanished: {p.skill.path}")
    target = p.target
    if (target.exists() or target.is_symlink()) and not force:
        raise TargetExists(f"{target} already exists (use --force to replace)")
    # deepest existing ancestor of the skills dir must be writable
    anc = p.dest.skills_dir
    while not anc.exists():
        anc = anc.parent
    if not os.access(anc, os.W_OK):
        raise MetaSkillsError(f"not writable: {anc}")
    if (
        p.method is Method.CUSTOM
        and rewire.get(p.skill.collection, source_rev(p.skill)) is None
    ):
        raise MetaSkillsError(f"no rewiring registered for {p.skill.collection}")


def execute(p: InstallPlan, *, force: bool = False) -> Path:
    """Perform the install; returns the target path."""
    preflight(p, force=force)
    skills_dir = p.dest.skills_dir
    skills_dir.mkdir(parents=True, exist_ok=True)
    target = p.target

    if p.method is Method.CUSTOM:
        rewiring = rewire.get(p.skill.collection, source_rev(p.skill))
        assert rewiring is not None  # preflight guarantees this
        rewiring(p.skill, p.dest)  # custom installs place their own files
    else:
        staged = skills_dir / f".staging-{p.skill.name}"
        fsutil.remove(staged)  # leftover from a crashed run
        try:
            if p.method is Method.COPY:
                shutil.copytree(
                    p.skill.path, staged, ignore=shutil.ignore_patterns(".git")
                )
            else:
                staged.symlink_to(p.skill.path)
            fsutil.swap(staged, target)
        except OSError as e:
            fsutil.remove(staged)
            raise MetaSkillsError(f"installing {p.skill.id} failed: {e}") from e

    manifest.record(
        skills_dir,
        skill_name=p.skill.name,
        skill_id=p.skill.id,
        method=p.method.value,
        source_rev=source_rev(p.skill),
    )
    # keep the manager's transient files (and symlinked skills) out of git
    if p.dest.kind in (DestKind.REPO, DestKind.DIR):
        names = (p.skill.name,) if p.method is Method.SYMLINK else ()
        gitutil.skills_gitignore_add(skills_dir, names)
    return target


def uninstall(dest: Dest, skill_name: str) -> None:
    try:
        fsutil.remove(dest.skills_dir / skill_name)
    except OSError as e:
        raise MetaSkillsError(f"removing {skill_name} failed: {e}") from e
    manifest.forget(dest.skills_dir, skill_name)
    gitutil.skills_gitignore_remove(dest.skills_dir, skill_name)
