"""Interactive CLI. Run via ./cli at the repo root."""

from __future__ import annotations

import sys

import click

from . import dest as dest_mod
from . import discover, install, manifest
from .model import Dest, DestKind, Method, Skill

# sensible default method per dest kind (CUSTOM is always explicit)
_DEFAULT_METHOD = {
    DestKind.HOME: Method.SYMLINK,  # my machine, keep pointing at this repo
    DestKind.REPO: Method.COPY,  # shared with collaborators -> snapshot
    DestKind.DIR: Method.SYMLINK,
}


@click.group()
def cli() -> None:
    """Personal skill storage & manager."""


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
@click.option("--method", type=click.Choice([m.value for m in Method]), default=None)
@click.option("--force", is_flag=True, help="replace an existing install")
@click.option("--yes", is_flag=True, help="skip confirmation")
def install_(
    skills: tuple[str, ...], dest_path: str, method: str | None, force: bool, yes: bool
):
    """Install SKILLS (ids, names, or substrings) into --dest.

    With no SKILLS argument, pick interactively.
    """
    try:
        dest = dest_mod.resolve(dest_path)
    except ValueError as e:
        raise click.ClickException(str(e))

    chosen = _select_skills(skills)
    m = Method(method) if method else _DEFAULT_METHOD[dest.kind]

    plans = [install.plan(s, dest, m) for s in chosen]
    click.echo(f"dest: {dest.skills_dir}  ({dest.kind.value})")
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
    """Show what is installed at --dest, flagging drift from current sources."""
    dest = dest_mod.resolve(dest_path)
    entries = manifest.load(dest.skills_dir)
    if not entries:
        click.echo(f"nothing recorded at {dest.skills_dir}")
        return
    by_id = {s.id: s for s in discover.all_skills()}
    for name, e in sorted(entries.items()):
        skill = by_id.get(e["skill"])
        if skill is None:
            state = click.style("source gone", fg="red")
        elif install.source_rev(skill) != e["source_rev"]:
            state = click.style("drifted (source rev changed)", fg="yellow")
        else:
            state = click.style("ok", fg="green")
        click.echo(f"  {name}  [{e['method']}]  {state}")


@cli.command()
@click.argument("skill_name")
@click.option("--dest", "dest_path", default=".", show_default=True)
def uninstall(skill_name: str, dest_path: str) -> None:
    """Remove an installed skill from --dest."""
    dest = dest_mod.resolve(dest_path)
    install.uninstall(dest, skill_name)
    click.secho(f"removed {dest.skills_dir / skill_name}", fg="green")


def _select_skills(queries: tuple[str, ...]) -> list[Skill]:
    if queries:
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

    # interactive pick
    skills = discover.all_skills()
    if not skills:
        raise click.ClickException("no skills found (are submodules initialized?)")
    for i, s in enumerate(skills, 1):
        click.echo(f"  {i:2d}. {s.id}")
    raw = click.prompt("skills to install (numbers, comma separated)")
    try:
        picks = [skills[int(n) - 1] for n in raw.replace(",", " ").split()]
    except (ValueError, IndexError):
        raise click.ClickException(f"bad selection: {raw!r}")
    return picks


def main() -> int:
    cli(prog_name="meta-skills")
    return 0


if __name__ == "__main__":
    sys.exit(main())
