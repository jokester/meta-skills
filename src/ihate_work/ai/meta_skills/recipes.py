"""Extraction recipes for REMOTE collections.

A *recipe* is the whole definition of a REMOTE collection: where upstream
lives, which revision we are pinned to, which part of its tree we fetch,
and how `extract.py` turns that tree into installable skills.

Why REMOTE exists at all: the shapes in `docs/external-collections.md`
assume a repo we can vendor as a submodule and install from directly.
A monorepo catalogue (shape E) breaks both halves of that — it is far too
big to vendor (OpenDesign is 3.5 GB), and its tree is not installable
as-is (duplicate registries, stubs, cross-bundle references, reference
material that is not a skill at all). So we pin a revision here, fetch a
sparse slice of it into a gitignored cache, and derive the installable
skills with a scripted, re-runnable extraction.

The pin lives in code, next to the extraction steps that assume that
tree's shape — bumping one without reviewing the other is the mistake
this layout is meant to make hard. `extract.py` re-checks upstream's shape
on every run (see `Root.min_bundles`) and fails loudly when it moved.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# A generator synthesizes bundles that do not exist upstream, from material
# that is not in skill form. (upstream tree, extract output dir) -> names.
Generator = Callable[[Path, Path], list[str]]


@dataclass(frozen=True)
class Root:
    """One directory of the upstream tree that holds skill bundles."""

    path: str  # relative to the upstream root, e.g. "skills"
    min_bundles: int  # sanity floor: fewer than this means the shape moved


@dataclass(frozen=True)
class Recipe:
    collection: str  # "<gh-user>/<repo>", the collection name we expose
    url: str
    rev: str  # full sha; the pin this extract is reproducible from
    summary: str  # one line, for `list` and the report
    sparse: tuple[str, ...] = ()  # tree paths to check out (cone mode)
    roots: tuple[Root, ...] = ()
    drop_dirs: frozenset[str] = frozenset()  # bundle names to never extract
    stub_marker: str | None = None  # body substring marking a content-free stub
    craft_dir: str | None = None  # dir holding `od.craft.requires` references
    # (pattern, replacement) pairs applied to bundle bodies, for links that
    # only resolved inside the monorepo
    link_rewrites: tuple[tuple[str, str], ...] = ()
    generators: tuple[Generator, ...] = field(default=())
    license_files: tuple[str, ...] = ("LICENSE",)


_REGISTRY: dict[str, Recipe] = {}


def register(recipe: Recipe) -> Recipe:
    _REGISTRY[recipe.collection] = recipe
    return recipe


def get(collection: str) -> Recipe | None:
    return _REGISTRY.get(collection)


def all_recipes() -> list[Recipe]:
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


# --- generators --------------------------------------------------------


_ROUTER_NAME = "open-design-design-systems"

_ROUTER_SKILL = """---
name: {name}
description: |
  {count} ready-made design systems as full design briefs plus CSS token
  files — brand-flavoured ones (Stripe, Linear, Notion, Apple, Vercel,
  Spotify, GitHub, Figma...) and style-flavoured ones (brutalism,
  editorial, glassmorphism, neobrutalism, neumorphism, retro, luxury...).
  Use when a design task needs a concrete visual system rather than
  improvised colors and type: "make it look like <brand>", "pick a design
  system", "give this a house style", "what tokens should I use", or
  before building any UI, deck, or page that has no design system yet.
---

# Design systems

{count} systems, each one a written brief plus a matching token file.
Reach for one *before* you start building, not after.

## How to use

1. **Pick.** Read `references/INDEX.md` — one line per system, with its
   category and the feel it produces. Grep it when the user named a brand
   or a mood; skim it when they did not.
2. **Read the brief in full.** `references/<slug>/DESIGN.md` is required
   context, not a skim: it carries the palette with its *roles*, the type
   scale, spacing, elevation, and the rationale that tells you which rules
   are load-bearing. Read it once, completely, before writing any markup.
3. **Bind the tokens.** `references/<slug>/tokens.css` holds the system as
   CSS custom properties — drop it in and reference the variables instead
   of hardcoding values. `design-tokens.json` is the same set in JSON, for
   when you are generating config rather than CSS.
4. **Stay inside the system.** If the brief gives you a palette, do not
   introduce a sixth accent because a section feels empty. Off-system
   improvisation is what makes generated UI read as generated.

## When the user names a brand we do not have

Pick the closest system in the same category and say which one you chose
and why. Do not invent a token file and label it with a brand name.

## Provenance

These are OpenDesign's bundled design-system packages, extracted at the
revision recorded in `ATTRIBUTION.md`. Each brief is an *interpretation*
of a public visual language, not an official artifact of the brand it is
named after, and the names are the property of their owners.
"""


def _read_tagline(design_md: Path) -> tuple[str, str]:
    """(category, tagline) from a DESIGN.md's leading blockquote lines."""
    category = tagline = ""
    for line in design_md.read_text(encoding="utf-8", errors="replace").splitlines()[
        :12
    ]:
        line = line.strip()
        if not line.startswith(">"):
            continue
        text = line.lstrip("> ").strip()
        if text.lower().startswith("category:"):
            category = text.split(":", 1)[1].strip()
        elif text and not tagline:
            tagline = text
    return category, tagline


def design_systems_router(src: Path, out: Path) -> list[str]:
    """Turn `design-systems/` into one router skill.

    Upstream keeps these as product packages, not skills — there is no
    SKILL.md anywhere under `design-systems/`, so a plain extraction would
    walk straight past the single richest thing in the repo. We synthesize
    the bundle that makes them reachable: an index the agent can grep, and
    the English brief + token files for each system (the 17 translations
    and the preview/fixture dirs are left behind — they are 80% of the
    weight and none of the value outside their own app).
    """
    systems_dir = src / "design-systems"
    if not systems_dir.is_dir():
        return []

    bundle = out / _ROUTER_NAME
    refs = bundle / "references"
    refs.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, str]] = []
    for d in sorted(p for p in systems_dir.iterdir() if p.is_dir()):
        if d.name.startswith("_"):  # _schema and friends are not systems
            continue
        design = d / "DESIGN.md"
        if not design.is_file():
            continue
        target = refs / d.name
        target.mkdir(parents=True, exist_ok=True)
        for fname in ("DESIGN.md", "tokens.css", "design-tokens.json"):
            f = d / fname
            if f.is_file():
                target.joinpath(fname).write_bytes(f.read_bytes())
        category, tagline = _read_tagline(design)
        rows.append((d.name, category or "—", tagline or "—"))

    if not rows:
        return []

    index = [
        "# Design system index",
        "",
        (
            f"{len(rows)} systems. Read the brief at "
            "`references/<slug>/DESIGN.md` in full before building."
        ),
        "",
        "| slug | category | feel |",
        "| --- | --- | --- |",
    ]
    index += [f"| `{s}` | {c} | {t} |" for s, c, t in rows]
    refs.joinpath("INDEX.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    bundle.joinpath("SKILL.md").write_text(
        _ROUTER_SKILL.format(name=_ROUTER_NAME, count=len(rows)), encoding="utf-8"
    )
    return [_ROUTER_NAME]


# --- recipes -----------------------------------------------------------

OPEN_DESIGN = register(
    Recipe(
        collection="nexu-io/open-design",
        url="https://github.com/nexu-io/open-design",
        rev="f5707c8cae7b61014c5e91e114b9aa07826df725",
        summary=(
            "OpenDesign — design workspace monorepo; we take its functional "
            "skills, its rendering templates, and its design-system library"
        ),
        # cone mode also brings the root files, which is where LICENSE lives
        sparse=("skills", "design-templates", "design-systems", "craft"),
        roots=(Root("skills", min_bundles=60), Root("design-templates", 80)),
        # 22 MB of marketing PNGs for OpenDesign's own landing page; anything
        # that cross-references it is cascade-dropped by the extractor
        drop_dirs=frozenset({"open-design-landing"}),
        # 85 of 163 `skills/` entries are frontmatter pointing at an upstream
        # we do not have — discoverable names with no workflow behind them
        stub_marker="catalogue entry advertises the skill",
        craft_dir="craft",
        generators=(design_systems_router,),
        # `../../design-systems/<slug>/DESIGN.md` escaped the bundle to reach
        # material that the router now carries as an ordinary sibling
        link_rewrites=(
            (
                r"\]\(\.\./\.\./design-systems/([A-Za-z0-9._-]+)/DESIGN\.md",
                rf"](../{_ROUTER_NAME}/references/\1/DESIGN.md",
            ),
        ),
    )
)
