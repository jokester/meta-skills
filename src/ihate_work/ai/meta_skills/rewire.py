"""CUSTOM install adaptations for specific upstreams.

Some upstreams ship their own install script (template instantiation,
multi-file layouts, ...). We keep the adaptation steps here, in our code,
pinned to (upstream_collection, upstream_rev) matching the submodule pin —
when a submodule is bumped, its rewiring must be revisited (the stale pin
makes the lookup fail loudly instead of silently doing the wrong thing).
"""

from __future__ import annotations

from collections.abc import Callable

from .model import Dest, Skill

# A rewiring takes the skill and resolved dest, and performs the install
# itself (including any template instantiation). It returns the target path.
Rewiring = Callable[[Skill, Dest], object]

# keyed by (collection, upstream_rev), e.g. ("obra/superpowers", "6fd4507...")
_REGISTRY: dict[tuple[str, str], Rewiring] = {}


def register(collection: str, rev: str):
    def deco(fn: Rewiring) -> Rewiring:
        _REGISTRY[(collection, rev)] = fn
        return fn

    return deco


def get(collection: str, rev: str | None) -> Rewiring | None:
    if rev is None:
        return None
    return _REGISTRY.get((collection, rev))


def known_collections() -> set[str]:
    return {c for c, _ in _REGISTRY}


# --- rewirings ---------------------------------------------------------
# @register("obra/superpowers", "<pinned rev>")
# def _superpowers(skill: Skill, dest: Dest): ...
