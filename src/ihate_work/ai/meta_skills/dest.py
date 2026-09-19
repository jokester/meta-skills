"""Classify and resolve install destinations.

Two axes: the *root* (HOME / REPO / DIR — where structurally) and the
*product* (which agent's convention — .claude, .codex, .pi, ... from
products.py). Both are surfaced to the caller instead of decided silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import Dest, DestKind
from .products import PRODUCTS, by_key


@dataclass(frozen=True)
class Root:
    """The structural half of a dest, before a product is chosen."""

    kind: DestKind
    path: Path


class AmbiguousRoot(Exception):
    """The path admits more than one root reading; the caller must ask.

    Typical case: a plain subdir inside a git repo — did they mean the
    enclosing repo or this dir itself? Never decide silently.
    """

    def __init__(self, path: Path, roots: list[Root]):
        self.path = path
        self.roots = roots
        super().__init__(f"ambiguous dest: {path}")


def dests_for_root(root: Root) -> list[Dest]:
    """One candidate Dest per product at this root."""
    out = []
    for p in PRODUCTS:
        skills = (
            p.global_skills.expanduser()
            if root.kind is DestKind.HOME
            else root.path / p.project_skills
        )
        out.append(
            Dest(kind=root.kind, root=root.path, skills_dir=skills, product=p.key)
        )
    return out


def is_configured(d: Dest) -> bool:
    """The product already has a presence at this dest."""
    if d.kind is DestKind.HOME:
        return d.skills_dir.is_dir()
    return (d.root / by_key(d.product).marker).is_dir()


def candidates(raw: str | Path) -> list[Dest]:
    """All plausible Dests for a user-supplied path.

    Returns one Dest per product for an unambiguous root (or a single Dest
    when the path itself names one product's global dir). Raises
    AmbiguousRoot when the root reading is unclear, ValueError when the
    path is no dest at all.
    """
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"not a directory: {path}")
    home = Path.home()

    if path == home:
        return dests_for_root(Root(DestKind.HOME, home))
    # a product-specific global location: ~/.codex, ~/.pi/agent/skills, ...
    for p in PRODUCTS:
        g = p.global_skills.expanduser()
        if path == g or (g.is_relative_to(path) and path.is_relative_to(home)):
            return [Dest(kind=DestKind.HOME, root=home, skills_dir=g, product=p.key)]

    # .git may be a dir or a file (worktrees, submodules)
    if (path / ".git").exists():
        return dests_for_root(Root(DestKind.REPO, path))

    if any((path / p.marker).is_dir() for p in PRODUCTS):
        return dests_for_root(Root(DestKind.DIR, path))

    enclosing = next((q for q in path.parents if (q / ".git").exists()), None)
    if enclosing is not None:
        raise AmbiguousRoot(
            path, [Root(DestKind.REPO, enclosing), Root(DestKind.DIR, path)]
        )

    markers = ", ".join(p.marker for p in PRODUCTS)
    raise ValueError(
        f"{path} is not a recognizable dest: not a global skill dir, "
        f"not a git repo root, and has none of: {markers}"
    )
