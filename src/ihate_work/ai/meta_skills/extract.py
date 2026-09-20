"""Derive installable skills from a REMOTE collection's upstream tree.

Extraction is scripted, never hand-curated: everything under `build/` is
reproducible from a recipe plus its pinned rev, so nothing here is an
artifact anyone has to maintain. Re-run it, diff the report, throw the
build away whenever.

The stages, in order:

  fetch      sparse, shallow clone of the pinned rev into a cache
  collect    bundles (dirs with SKILL.md) under the recipe's roots
  filter     denylisted dirs, content-free stubs, then cascade-drop any
             bundle left pointing at something we dropped
  normalize  make the frontmatter survive a flat install: `name` must
             match the dir it lives in, `description` must exist
  enrich     inline the craft references the upstream daemon used to
             inject at runtime; rewrite repo-root links to sibling links
  generate   synthesize bundles for material that is not in skill form
  attribute  carry licenses, record origin + rev + our modifications
  verify     re-check the shape; fail loudly rather than ship a bad build

Only the last step mutates `build/<collection>`, by swapping a fully
staged tree into place (see `fsutil`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from . import fsutil
from .errors import MetaSkillsError
from .recipes import Recipe

STATE_NAME = ".extract.json"

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)\Z", re.DOTALL)
_TOP_KEY = re.compile(r"^([A-Za-z_][\w-]*)[ \t]*:", re.MULTILINE)
_SIBLING_LINK = re.compile(r"\]\(\.\./([A-Za-z0-9._-]+)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\((\.\./[^)\s]+)\)")


def sibling_targets(text: str) -> set[str]:
    """Bundle names a body points at with `../<name>/...`.

    `../..` escapes the collection entirely rather than naming a sibling,
    so it is not a target — reading it as one is how a link out to the
    monorepo gets mistaken for a reference to a bundle called `..`.
    """
    return {t for t in _SIBLING_LINK.findall(text) if t not in ("..", ".")}


# --- paths -------------------------------------------------------------


def cache_dir(repo_root: Path, collection: str) -> Path:
    return repo_root / ".cache" / collection


def build_dir(repo_root: Path, collection: str) -> Path:
    return repo_root / "build" / collection


def state_of(repo_root: Path, collection: str) -> dict:
    """The recorded state of an extract, or {} when never extracted."""
    p = build_dir(repo_root, collection) / STATE_NAME
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return {}


def is_stale(repo_root: Path, recipe: Recipe) -> bool:
    state = state_of(repo_root, recipe.collection)
    return bool(state) and state.get("rev") != recipe.rev


# --- frontmatter -------------------------------------------------------


def split_frontmatter(text: str) -> tuple[str | None, str]:
    m = _FRONTMATTER.match(text)
    return (m.group(1), m.group(2)) if m else (None, text)


def join_frontmatter(fm: str, body: str) -> str:
    return f"---\n{fm}\n---\n{body}"


def parse_meta(fm: str | None) -> dict:
    """Frontmatter as a dict; unparseable frontmatter reads as empty."""
    if not fm:
        return {}
    try:
        meta = yaml.safe_load(fm)
    except yaml.YAMLError:
        return {}
    return meta if isinstance(meta, dict) else {}


def _top_keys(fm: str) -> set[str]:
    return set(_TOP_KEY.findall(fm))


def set_scalar(fm: str, key: str, value: str) -> str:
    """Rewrite (or prepend) a top-level scalar key.

    Line surgery on purpose: round-tripping these through a YAML dumper
    would reflow 189 hand-written frontmatters — multi-line descriptions,
    CJK, trigger lists — and bury the one line we meant to change.
    """
    line = f"{key}: {value}"
    if key in _top_keys(fm):
        out, replaced, depth_skip = [], False, False
        for ln in fm.splitlines():
            if not replaced and re.match(rf"^{re.escape(key)}[ \t]*:", ln):
                out.append(line)
                replaced = True
                # drop a block scalar's continuation lines, if any
                depth_skip = ln.rstrip().endswith(("|", ">", "|-", ">-"))
                continue
            if depth_skip:
                if ln.startswith((" ", "\t")) or not ln.strip():
                    continue
                depth_skip = False
            out.append(ln)
        return "\n".join(out)
    return f"{line}\n{fm}"


# --- model -------------------------------------------------------------


@dataclass
class Bundle:
    name: str
    src: Path
    root: str
    meta: dict = field(default_factory=dict)


@dataclass
class Result:
    collection: str
    rev: str
    out: Path
    kept: list[str] = field(default_factory=list)
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # name, root, why
    renamed: list[tuple[str, str]] = field(default_factory=list)  # dir, old name
    described: list[str] = field(default_factory=list)
    crafted: list[tuple[str, list[str]]] = field(default_factory=list)
    relinked: list[str] = field(default_factory=list)
    neutralized: list[tuple[str, list[str]]] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    size_bytes: int = 0

    @property
    def drops_by_reason(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for name, _root, why in self.dropped:
            out.setdefault(why, []).append(name)
        return out


# --- fetch -------------------------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
        )
    except FileNotFoundError as e:
        raise MetaSkillsError("git not found on PATH") from e
    except subprocess.CalledProcessError as e:
        cmd = " ".join(args[:3])
        raise MetaSkillsError(f"git {cmd} failed: {e.stderr.strip()}") from e
    return r.stdout.strip()


def fetch(recipe: Recipe, cache: Path) -> Path:
    """Materialize the pinned rev in the cache; a no-op when already there.

    Shallow, blobless and sparse: a full clone of a monorepo this size is
    gigabytes, and we want four directories of it. The rev is fetched by
    sha rather than by branch, so the pin keeps resolving after upstream
    moves on.
    """
    cache.mkdir(parents=True, exist_ok=True)
    if not (cache / ".git").is_dir():
        _git(cache, "init", "--quiet")
        _git(cache, "remote", "add", "origin", recipe.url)
    elif _git(cache, "rev-parse", "HEAD") == recipe.rev:
        return cache

    if recipe.sparse:
        _git(cache, "sparse-checkout", "init", "--cone")
        _git(cache, "sparse-checkout", "set", *recipe.sparse)
    _git(
        cache,
        "fetch",
        "--depth",
        "1",
        "--filter=blob:none",
        "--no-tags",
        "origin",
        recipe.rev,
    )
    _git(cache, "checkout", "--quiet", "--detach", recipe.rev)
    return cache


# --- stages ------------------------------------------------------------


def collect(recipe: Recipe, src: Path) -> list[Bundle]:
    """Bundles directly under each root, with their shape re-checked."""
    bundles: list[Bundle] = []
    for root in recipe.roots:
        rdir = src / root.path
        if not rdir.is_dir():
            raise MetaSkillsError(
                f"{recipe.collection}: upstream has no {root.path}/ at "
                f"{recipe.rev[:7]} — the tree moved; revisit the recipe"
            )
        found = [
            Bundle(name=d.name, src=d, root=root.path)
            for d in sorted(rdir.iterdir())
            if d.is_dir() and (d / "SKILL.md").is_file()
        ]
        if len(found) < root.min_bundles:
            raise MetaSkillsError(
                f"{recipe.collection}: {root.path}/ has {len(found)} bundles, "
                f"expected at least {root.min_bundles} — the tree moved; "
                "revisit the recipe"
            )
        bundles += found
    return bundles


def filter_bundles(
    recipe: Recipe, bundles: list[Bundle], result: Result
) -> list[Bundle]:
    """Drop what should not ship, then settle the consequences.

    The two drop reasons do not cascade alike. A *stub* has no workflow
    behind it, so a bundle whose instructions say "read ../that-one" is
    left pointing at nothing real and has to go too. A *denylisted* bundle
    is our own call — usually weight — and the bundles that mention it are
    still perfectly good, so they stay and their dead link is neutralized
    in `enrich`. Getting this backwards silently deletes good skills.
    """
    keep: list[Bundle] = []
    dropped_stubs: set[str] = set()
    for b in bundles:
        if b.name in recipe.drop_dirs:
            result.dropped.append((b.name, b.root, "denylisted by the recipe"))
            continue
        text = (b.src / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        b.meta = parse_meta(fm)
        if recipe.stub_marker and recipe.stub_marker in body:
            result.dropped.append(
                (b.name, b.root, "catalogue stub: frontmatter only, no workflow")
            )
            dropped_stubs.add(b.name)
            continue
        keep.append(b)

    while True:
        if not dropped_stubs:
            break
        survivors = []
        for b in keep:
            text = (b.src / "SKILL.md").read_text(encoding="utf-8", errors="replace")
            missing = sorted(sibling_targets(text) & dropped_stubs)
            if missing:
                result.dropped.append(
                    (b.name, b.root, f"relies on dropped stub {', '.join(missing)}")
                )
                dropped_stubs.add(b.name)
                continue
            survivors.append(b)
        if len(survivors) == len(keep):
            break
        keep = survivors
    return keep


def stage(bundles: list[Bundle], staging: Path) -> None:
    for b in bundles:
        shutil.copytree(
            b.src,
            staging / b.name,
            ignore=shutil.ignore_patterns(".git", "node_modules", "__pycache__"),
        )


def normalize(bundles: list[Bundle], staging: Path, result: Result) -> None:
    """Make each bundle survive a flat install on its own.

    Products key a skill by its frontmatter `name`, so a bundle whose name
    disagrees with its directory installs under one identity and answers to
    another. We move the *frontmatter*, never the directory — 39 bundles
    reach each other by relative path, and renaming dirs would cut those.
    """
    for b in bundles:
        p = staging / b.name / "SKILL.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        if fm is None:  # no frontmatter at all: give it the minimum
            fm, body = f"name: {b.name}", text
            result.warnings.append(f"{b.name}: no frontmatter upstream; synthesized")

        declared = b.meta.get("name")
        if declared != b.name:
            fm = set_scalar(fm, "name", b.name)
            result.renamed.append((b.name, str(declared)))

        if not str(b.meta.get("description") or "").strip():
            fm = set_scalar(fm, "description", _synth_description(b, body))
            result.described.append(b.name)

        p.write_text(join_frontmatter(fm, body), encoding="utf-8")


def _neutralize(body: str, names: set[str]) -> tuple[str, list[str]]:
    """Defuse links to bundles this extract does not ship.

    Left as links they are an invitation to open a path that is not there;
    as inline code they still tell the reader what upstream pointed at.
    """
    cut: list[str] = []

    def sub(m: re.Match[str]) -> str:
        target = m.group(2)
        head = target.removeprefix("../").split("/", 1)[0]
        if head in names:
            return m.group(0)
        cut.append(target)
        label = m.group(1).strip()
        if not label or target in label:
            return f"`{target}` (not bundled in this extract)"
        return f"{label} (`{target}` — not bundled in this extract)"

    return _MD_LINK.sub(sub, body), cut


def _synth_description(b: Bundle, body: str) -> str:
    for key in ("en_description", "zh_description"):
        value = str(b.meta.get(key) or "").strip().splitlines()
        if value:
            return value[0]
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", ">", "-", "|")):
            return line[:300]
    return f"{b.name} — extracted from OpenDesign; upstream gave no description."


def enrich(
    recipe: Recipe,
    bundles: list[Bundle],
    src: Path,
    staging: Path,
    result: Result,
    extra_names: Collection[str] = (),
) -> None:
    """Restore context the upstream runtime used to supply, not the file.

    Three losses happen the moment a bundle leaves its app. Craft
    references were composed into the prompt by the daemon from
    `od.craft.requires`; here they have to be files the bundle carries.
    Links written as repo paths (`design-templates/x/SKILL.md`) only
    resolved from the monorepo root; installed flat, the same target is a
    sibling. And a link to something this extract does not ship has to
    stop looking like a file the agent can open.
    """
    roots = tuple(r.path for r in recipe.roots)
    names = {b.name for b in bundles} | set(extra_names)
    craft_dir = src / recipe.craft_dir if recipe.craft_dir else None

    for b in bundles:
        p = staging / b.name / "SKILL.md"
        text = p.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)

        rewritten = body
        for root in roots:
            rewritten = re.sub(
                rf"\]\({re.escape(root)}/([A-Za-z0-9._-]+)/",
                lambda m: f"](../{m.group(1)}/" if m.group(1) in names else m.group(0),
                rewritten,
            )
        for pattern, repl in recipe.link_rewrites:
            rewritten = re.sub(pattern, repl, rewritten)
        if rewritten != body:
            body = rewritten
            result.relinked.append(b.name)

        body, cut = _neutralize(body, names)
        if cut:
            result.neutralized.append((b.name, cut))

        wanted = (b.meta.get("od") or {}).get("craft", {}).get("requires") or []
        if craft_dir and wanted:
            got = []
            refs = staging / b.name / "references" / "craft"
            for slug in wanted:
                f = craft_dir / f"{slug}.md"
                if not f.is_file():
                    result.warnings.append(f"{b.name}: no craft reference {slug}.md")
                    continue
                refs.mkdir(parents=True, exist_ok=True)
                refs.joinpath(f"{slug}.md").write_bytes(f.read_bytes())
                got.append(slug)
            if got:
                listed = ", ".join(f"`references/craft/{s}.md`" for s in got)
                body = (
                    "> **Craft references — read these first.** " + listed + "\n"
                    "> They are the brand-agnostic rules this bundle declares as\n"
                    "> required, inlined here because nothing injects them for you.\n\n"
                ) + body.lstrip("\n")
                result.crafted.append((b.name, got))

        p.write_text(join_frontmatter(fm or "", body), encoding="utf-8")


def attribute(recipe: Recipe, src: Path, staging: Path, result: Result) -> None:
    """Carry the licenses, and say what we changed. Apache-2.0 §4(a)-(b).

    Per bundle, not just once at the root: a bundle is the unit that gets
    installed and shared, and it has to arrive at a dest carrying the
    license and the statement of what we changed.
    """
    upstream_license = None
    for fname in recipe.license_files:
        f = src / fname
        if f.is_file():
            staging.joinpath(fname).write_bytes(f.read_bytes())
            if upstream_license is None:
                upstream_license = f.read_bytes()
        else:
            result.warnings.append(f"upstream has no {fname} to carry")

    renamed = dict(result.renamed)
    crafted = dict(result.crafted)
    neutralized = dict(result.neutralized)
    for name in sorted({*result.kept, *result.generated}):
        bundle = staging / name
        if not bundle.is_dir():
            continue
        changes = ["extracted from the monorepo into a standalone skill dir"]
        if name in renamed:
            changes.append(
                f"frontmatter `name` set to `{name}` (was `{renamed[name]}`)"
            )
        if name in result.described:
            changes.append("`description` synthesized (upstream had none)")
        if name in crafted:
            changes.append(
                "craft references inlined under `references/craft/`: "
                + ", ".join(crafted[name])
            )
        if name in result.relinked:
            changes.append("links rewritten to resolve inside this extract")
        if name in neutralized:
            changes.append(
                "links to material this extract does not ship defused: "
                + ", ".join(f"`{t}`" for t in neutralized[name])
            )
        if name in result.generated:
            changes = ["synthesized by meta-skills from upstream material"]
        own = (bundle / "LICENSE").is_file()
        if not own and upstream_license is not None:
            bundle.joinpath("LICENSE").write_bytes(upstream_license)
        bundle.joinpath("ATTRIBUTION.md").write_text(
            "\n".join(
                [
                    "# Attribution",
                    "",
                    f"Extracted by meta-skills from **{recipe.collection}**.",
                    "",
                    f"- Source: {recipe.url}",
                    f"- Revision: `{recipe.rev}`",
                    "- Upstream license: Apache-2.0",
                    (
                        "- License: see this dir's `LICENSE` — "
                        + ("the bundle's own" if own else "the upstream repo's")
                    ),
                    (
                        "- Declared upstream of origin: "
                        f"{_declared_upstream(bundle) or '—'}"
                    ),
                    "",
                    "## Modifications",
                    "",
                    *[f"- {c}" for c in changes],
                    "",
                ]
            ),
            encoding="utf-8",
        )


def _declared_upstream(bundle: Path) -> str | None:
    fm, _ = split_frontmatter(
        (bundle / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    )
    return (parse_meta(fm).get("od") or {}).get("upstream")


def verify(staging: Path, result: Result) -> None:
    """Last gate before the swap: never publish a build we know is broken."""
    names = {p.name for p in staging.iterdir() if p.is_dir()}
    for name in sorted(names):
        skill = staging / name / "SKILL.md"
        if not skill.is_file():
            raise MetaSkillsError(f"extract produced {name}/ with no SKILL.md")
        fm, _ = split_frontmatter(skill.read_text(encoding="utf-8", errors="replace"))
        meta = parse_meta(fm)
        if meta.get("name") != name:
            raise MetaSkillsError(
                f"extract left {name}/ declaring name={meta.get('name')!r}"
            )
        if not str(meta.get("description") or "").strip():
            raise MetaSkillsError(f"extract left {name}/ without a description")

    for name in sorted(names):
        text = (staging / name / "SKILL.md").read_text(
            encoding="utf-8", errors="replace"
        )
        for target in sorted(sibling_targets(text) - names):
            result.warnings.append(f"{name}: dangling sibling reference ../{target}")


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


# --- orchestration -----------------------------------------------------


def run(recipe: Recipe, repo_root: Path, *, do_fetch: bool = True) -> Result:
    """Fetch (optionally), extract, and publish `build/<collection>`."""
    cache = cache_dir(repo_root, recipe.collection)
    if do_fetch:
        fetch(recipe, cache)
    if not cache.is_dir() or not (cache / ".git").is_dir():
        raise MetaSkillsError(
            f"no cache for {recipe.collection} at {cache} — run without --no-fetch"
        )
    head = _git(cache, "rev-parse", "HEAD")
    if head != recipe.rev:
        raise MetaSkillsError(
            f"cache is at {head[:7]}, recipe pins {recipe.rev[:7]} — "
            "re-run without --no-fetch"
        )

    out = build_dir(repo_root, recipe.collection)
    staging = out.parent / f".staging-{out.name}"
    fsutil.remove(staging)
    staging.mkdir(parents=True)

    result = Result(collection=recipe.collection, rev=recipe.rev, out=out)
    try:
        bundles = filter_bundles(recipe, collect(recipe, cache), result)
        result.kept = sorted(b.name for b in bundles)
        stage(bundles, staging)
        normalize(bundles, staging, result)
        for gen in recipe.generators:
            result.generated += gen(cache, staging)
        enrich(recipe, bundles, cache, staging, result, set(result.generated))
        attribute(recipe, cache, staging, result)
        verify(staging, result)
        result.size_bytes = _dir_size(staging)
        staging.joinpath(STATE_NAME).write_text(
            json.dumps(
                {
                    "collection": recipe.collection,
                    "url": recipe.url,
                    "rev": recipe.rev,
                    "extracted_at": datetime.now(UTC).isoformat(timespec="seconds"),
                    "kept": result.kept,
                    "generated": result.generated,
                    "dropped": {n: w for n, _r, w in result.dropped},
                    "warnings": result.warnings,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        fsutil.swap(staging, out)
    except Exception:
        fsutil.remove(staging)
        raise
    return result


def render_report(recipe: Recipe, result: Result) -> str:
    """The committed audit trail: what this build contains and what it lost."""
    mb = result.size_bytes / 1_000_000
    lines = [
        f"# Extract — {result.collection}",
        "",
        "Generated by `./cli extract`; do not edit. Re-run the command to",
        "refresh it after bumping the pin in `recipes.py`.",
        "",
        f"- Source: {recipe.url}",
        f"- Revision: `{result.rev}`",
        f"- Output: `build/{result.collection}/` (gitignored, rebuildable)",
        (
            f"- Bundles: {len(result.kept)} extracted + "
            f"{len(result.generated)} generated, {mb:.1f} MB"
        ),
        "",
        "## Generated",
        "",
    ]
    lines += [
        f"- `{n}` — synthesized from material that ships no SKILL.md"
        for n in result.generated
    ] or ["- (none)"]
    lines += ["", "## Dropped", ""]
    for why, names in sorted(result.drops_by_reason.items()):
        lines.append(f"**{why}** — {len(names)}")
        lines.append("")
        lines.append("> " + ", ".join(f"`{n}`" for n in sorted(names)))
        lines.append("")
    if not result.dropped:
        lines += ["- (none)", ""]
    lines += ["## Normalized", ""]
    lines += [
        f"- `name` corrected in {len(result.renamed)}: "
        + ", ".join(f"`{d}` (was `{o}`)" for d, o in sorted(result.renamed))
        if result.renamed
        else "- no `name` corrections needed",
        f"- `description` synthesized in {len(result.described)}: "
        + ", ".join(f"`{n}`" for n in sorted(result.described))
        if result.described
        else "- no descriptions synthesized",
        f"- craft references inlined in {len(result.crafted)}: "
        + ", ".join(f"`{n}` ({', '.join(c)})" for n, c in sorted(result.crafted))
        if result.crafted
        else "- no craft references to inline",
        f"- links rewritten in {len(result.relinked)}: "
        + ", ".join(f"`{n}`" for n in sorted(result.relinked))
        if result.relinked
        else "- no links rewritten",
        f"- dead links defused in {len(result.neutralized)}: "
        + ", ".join(
            f"`{n}` (" + ", ".join(f"`{t}`" for t in ts) + ")"
            for n, ts in sorted(result.neutralized)
        )
        if result.neutralized
        else "- no dead links to defuse",
        "",
    ]
    lines += ["## Warnings", ""]
    lines += [f"- {w}" for w in result.warnings] or ["- (none)"]
    lines += [
        "",
        "## Extracted",
        "",
        "> " + ", ".join(f"`{n}`" for n in result.kept),
        "",
    ]
    return "\n".join(lines)
