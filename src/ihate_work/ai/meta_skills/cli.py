"""Interactive CLI. Run via ./cli at the repo root."""

from __future__ import annotations

import sys

import click

from . import dest as dest_mod
from . import discover, install, manifest, tui
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
    except ValueError as e:
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
        if not col.initialized:
            click.secho(
                f"{col.name}  (not initialized — run: git submodule update --init {col.name})",
                fg="yellow",
            )
            continue
        click.secho(col.name, bold=True)
        for s in col.skills:
            click.echo(f"  {s.name}")
        if not col.skills:
            click.echo("  (no SKILL.md found)")


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

    plans = [install.plan(s, d, m) for d in dests for s in chosen]
    for p in plans:
        click.echo(f"  {p.skill.id}  --{p.method.value}-->  {p.target}")
        for w in p.warnings:
            click.secho(f"  ! {w}", fg="yellow")
    if not (yes or click.confirm("proceed?", default=True)):
        raise click.Abort()

    for p in plans:
        target = install.execute(p, force=force)
        click.secho(f"installed {p.skill.id} -> {target}", fg="green")


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
            if skill is None:
                state = click.style("source gone", fg="red")
            elif install.source_rev(skill) != e["source_rev"]:
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

    for d, name in picked:
        install.uninstall(d, name)
        click.secho(f"removed {d.skills_dir / name}", fg="green")


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
