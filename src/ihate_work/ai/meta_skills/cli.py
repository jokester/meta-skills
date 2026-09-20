"""Interactive CLI. Run via ./cli at the repo root."""

from __future__ import annotations

import sys

import click

from . import dest as dest_mod
from . import discover, extract, install, manifest, recipes, tui
from .errors import MetaSkillsError, TargetExists
from .model import Dest, DestKind, Method, Skill
from .products import PRODUCTS

# sensible default method per dest kind (CUSTOM is always explicit)
_DEFAULT_METHOD = {
    DestKind.HOME: Method.SYMLINK,  # my machine, keep pointing at this repo
    DestKind.REPO: Method.COPY,  # shared with collaborators -> snapshot
    DestKind.DIR: Method.SYMLINK,
}

_PRODUCT_KEYS = [p.key for p in PRODUCTS]


@click.group()
def cli() -> None:
    """Personal skill storage & manager."""


def _tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _root_dests(dest_path: str) -> list[Dest]:
    """Resolve a dest path to per-product candidates.

    On root ambiguity: prompt (TTY) or fail loudly — never walk up silently.
    """
    try:
        return dest_mod.candidates(dest_path)
    except dest_mod.AmbiguousRoot as e:
        if _tty():
            return dest_mod.dests_for_root(tui.pick_root(e))
        options = "; ".join(f"{r.kind.value}: {r.path}" for r in e.roots)
        markers = ", ".join(p.marker for p in PRODUCTS)
        raise click.ClickException(
            f"{e.path} is ambiguous ({options}) — point --dest at the repo "
            f"root, or at a dir that already contains one of: {markers}"
        )
    except MetaSkillsError as e:
        raise click.ClickException(str(e))


def _narrow_products(cands: list[Dest], product_flags: tuple[str, ...]) -> list[Dest]:
    """Pick which product conventions to target among the candidates."""
    if product_flags:
        picked = [d for d in cands if d.product in product_flags]
        missing = set(product_flags) - {d.product for d in picked}
        if missing:
            raise click.ClickException(
                f"--product {', '.join(sorted(missing))} not applicable here"
            )
        return picked
    if len(cands) == 1:
        return cands
    configured = [d for d in cands if dest_mod.is_configured(d)]
    if _tty():
        return tui.pick_products(cands)
    if len(configured) == 1:
        return configured
    state = (
        f"{len(configured)} product dirs present"
        if configured
        else "no product dir present"
    )
    raise click.ClickException(
        f"{state} at this dest — pass --product ({'|'.join(_PRODUCT_KEYS)})"
    )


@cli.command("list")
def list_() -> None:
    """List all known skills, grouped by collection."""
    for col in discover.discover():
        if col.hint and not col.skills:
            click.secho(f"{col.name}  ({col.hint})", fg="yellow")
            continue
        click.secho(col.name, bold=True)
        if col.hint:
            click.secho(f"  ! {col.hint}", fg="yellow")
        for s in col.skills:
            click.echo(f"  {s.name}")
        if not col.skills:
            click.echo("  (no SKILL.md found)")


@cli.command("extract")
@click.argument("collections", nargs=-1)
@click.option(
    "--no-fetch", is_flag=True, help="use the cache as-is; never touch the network"
)
def extract_(collections: tuple[str, ...], no_fetch: bool) -> None:
    """Rebuild COLLECTIONS' skills from their pinned upstream (default: all).

    Everything the extract produces lives under build/ and is derived: it
    is safe to delete, and re-running this reproduces it from the rev
    pinned in recipes.py. The committed side is the report under
    docs/extracts/, which is what a bumped pin should be reviewed through.
    """
    chosen = recipes.all_recipes()
    if collections:
        by_name = {r.collection: r for r in chosen}
        unknown = sorted(set(collections) - set(by_name))
        if unknown:
            known = ", ".join(sorted(by_name)) or "(none registered)"
            raise click.ClickException(
                f"no recipe for {', '.join(unknown)} — known: {known}"
            )
        chosen = [by_name[c] for c in collections]

    n_failed = 0
    for recipe in chosen:
        click.secho(f"{recipe.collection}  @ {recipe.rev[:7]}", bold=True)
        try:
            result = extract.run(recipe, discover.REPO_ROOT, do_fetch=not no_fetch)
        except MetaSkillsError as e:
            n_failed += 1
            click.secho(f"  failed: {e}", fg="red")
            continue
        report = (
            discover.REPO_ROOT
            / "docs"
            / "extracts"
            / f"{recipe.collection.replace('/', '-')}.md"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(extract.render_report(recipe, result), encoding="utf-8")
        for w in result.warnings:
            click.secho(f"  ! {w}", fg="yellow")
        click.secho(
            f"  {len(result.kept)} extracted + {len(result.generated)} generated, "
            f"{len(result.dropped)} dropped, "
            f"{result.size_bytes / 1_000_000:.1f} MB -> {result.out}",
            fg="green",
        )
        click.echo(f"  report: {report.relative_to(discover.REPO_ROOT)}")
    if n_failed:
        sys.exit(1)


@cli.command("install")
@click.argument("skills", nargs=-1)
@click.option(
    "--dest", "dest_path", default=".", show_default=True, help="install destination"
)
@click.option(
    "--product",
    "products",
    multiple=True,
    type=click.Choice(_PRODUCT_KEYS),
    help="product convention(s) to install for; repeatable",
)
@click.option("--method", type=click.Choice([m.value for m in Method]), default=None)
@click.option("--force", is_flag=True, help="replace an existing install")
@click.option("--yes", is_flag=True, help="skip confirmation")
def install_(
    skills: tuple[str, ...],
    dest_path: str,
    products: tuple[str, ...],
    method: str | None,
    force: bool,
    yes: bool,
):
    """Install SKILLS (ids, names, or substrings) into --dest.

    With no SKILLS argument, run the interactive wizard instead
    (skill checkboxes, dest path, products, method).
    """
    wizard = not skills
    if wizard:
        chosen = tui.pick_skills(discover.discover())
        dest_path = tui.pick_dest_path(dest_path)
    else:
        chosen = _match_skills(skills)

    dests = _narrow_products(_root_dests(dest_path), products)

    if method:
        m = Method(method)
    elif wizard:
        m = tui.pick_method(_DEFAULT_METHOD[dests[0].kind])
    else:
        m = _DEFAULT_METHOD[dests[0].kind]

    # validate everything BEFORE confirming or mutating anything
    try:
        plans = [install.plan(s, d, m) for d in dests for s in chosen]
    except MetaSkillsError as e:
        raise click.ClickException(str(e))

    viable: list = []
    n_skipped = n_failed = 0
    for p in plans:
        try:
            install.preflight(p, force=force)
        except TargetExists:
            n_skipped += 1
            click.secho(
                f"  {p.skill.id}  (skip: {p.target} exists — use --force)",
                fg="yellow",
            )
            continue
        except MetaSkillsError as e:
            n_failed += 1
            click.secho(f"  {p.skill.id}  (cannot install: {e})", fg="red")
            continue
        viable.append(p)
        click.echo(f"  {p.skill.id}  --{p.method.value}-->  {p.target}")
    # each warning once per run, not once per skill
    for w in dict.fromkeys(w for p in plans for w in p.warnings):
        click.secho(f"! {w}", fg="yellow")

    n_installed = 0
    if viable and not (yes or click.confirm("proceed?", default=True)):
        raise click.Abort()
    for p in viable:
        try:
            target = install.execute(p, force=force)
        except MetaSkillsError as e:
            n_failed += 1
            click.secho(f"failed {p.skill.id}: {e}", fg="red")
            continue
        n_installed += 1
        click.secho(f"installed {p.skill.id} -> {target}", fg="green")

    summary = f"{n_installed} installed"
    if n_skipped:
        summary += f", {n_skipped} skipped (already exist — use --force)"
    if n_failed:
        summary += f", {n_failed} failed"
    click.echo(summary)
    if n_failed:
        sys.exit(1)


@cli.command()
@click.option("--dest", "dest_path", default=".", show_default=True)
def status(dest_path: str) -> None:
    """Show what is installed at --dest (all products), flagging drift."""
    by_id = {s.id: s for s in discover.all_skills()}
    shown = False
    for d in _root_dests(dest_path):
        entries = manifest.load(d.skills_dir)
        if not entries:
            continue
        shown = True
        click.secho(f"{d.product}: {d.skills_dir}", bold=True)
        for name, e in sorted(entries.items()):
            skill = by_id.get(e["skill"])
            current = install.source_rev(skill) if skill else None
            if skill is None:
                state = click.style("source gone", fg="red")
            elif e["source_rev"] is None or current is None:
                state = click.style("provenance unknown", fg="yellow")
            elif current != e["source_rev"]:
                state = click.style("drifted (source rev changed)", fg="yellow")
            else:
                state = click.style("ok", fg="green")
            click.echo(f"  {name}  [{e['method']}]  {state}")
    if not shown:
        click.echo(f"nothing recorded at {dest_path}")


@cli.command()
@click.argument("skill_names", nargs=-1)
@click.option("--dest", "dest_path", default=".", show_default=True)
@click.option(
    "--product",
    "products",
    multiple=True,
    type=click.Choice(_PRODUCT_KEYS),
    help="only remove from these product dirs; repeatable",
)
@click.option("--yes", is_flag=True, help="skip confirmation")
def uninstall(
    skill_names: tuple[str, ...],
    dest_path: str,
    products: tuple[str, ...],
    yes: bool,
) -> None:
    """Remove installed skills from --dest.

    With no SKILL_NAMES argument, pick interactively from what the dest's
    manifests record (across all product dirs).
    """
    cands = _root_dests(dest_path)
    if products:
        cands = [d for d in cands if d.product in products]
    recorded = [
        (d, name, e)
        for d in cands
        for name, e in sorted(manifest.load(d.skills_dir).items())
    ]

    if skill_names:
        picked = []
        for name in skill_names:
            hits = [(d, n) for d, n, _ in recorded if n == name]
            if not hits:
                raise click.ClickException(f"{name!r} is not recorded at this dest")
            picked.extend(hits)
    else:
        if not recorded:
            click.echo(f"nothing recorded at {dest_path}")
            return
        picked = tui.pick_installed(recorded)

    for d, name in picked:
        click.echo(f"  will remove {d.skills_dir / name}")
    if not (yes or click.confirm("proceed?", default=False)):
        raise click.Abort()

    n_failed = 0
    for d, name in picked:
        try:
            install.uninstall(d, name)
        except MetaSkillsError as e:
            n_failed += 1
            click.secho(f"failed {name}: {e}", fg="red")
            continue
        click.secho(f"removed {d.skills_dir / name}", fg="green")
    if n_failed:
        sys.exit(1)


def _match_skills(queries: tuple[str, ...]) -> list[Skill]:
    chosen: list[Skill] = []
    for q in queries:
        matches = discover.find_skill(q)
        if not matches:
            raise click.ClickException(f"no skill matches {q!r}")
        if len(matches) > 1:
            ids = ", ".join(s.id for s in matches)
            raise click.ClickException(f"{q!r} is ambiguous: {ids}")
        chosen.extend(matches)
    return chosen


def main() -> int:
    cli(prog_name="meta-skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
