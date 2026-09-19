"""Interactive terminal prompts (questionary-based).

Only cli.py calls these; everything here needs a TTY and raises a clean
ClickException when there is none, so scripted use (--yes + explicit args)
never lands in a prompt.
"""

from __future__ import annotations

import sys

import click
import questionary

from .dest import AmbiguousRoot, Root, is_configured
from .discover import Collection
from .model import Dest, DestKind, Method, Skill
from .products import by_key


def _ensure_tty() -> None:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise click.ClickException(
            "interactive mode needs a TTY; pass skill names / --yes explicitly"
        )


def _ask(question):
    answer = question.ask()
    if answer is None:  # ctrl-c / ctrl-d
        raise click.Abort()
    return answer


def pick_skills(collections: list[Collection]) -> list[Skill]:
    """Checkbox multi-select over all skills, grouped by collection."""
    _ensure_tty()
    choices: list = []
    for col in collections:
        if not col.skills:
            continue
        choices.append(questionary.Separator(f"── {col.name} ──"))
        choices.extend(questionary.Choice(title=s.name, value=s) for s in col.skills)
    if not choices:
        raise click.ClickException("no skills found (are submodules initialized?)")
    picked = _ask(
        questionary.checkbox(
            "skills to install (space = toggle, enter = done)", choices=choices
        )
    )
    if not picked:
        raise click.ClickException("nothing selected")
    return picked


def pick_dest_path(default: str = ".") -> str:
    _ensure_tty()
    return _ask(
        questionary.path("install dest", default=default, only_directories=True)
    )


_ROOT_LABEL = {
    DestKind.REPO: "the enclosing git repo",
    DestKind.DIR: "this dir itself",
    DestKind.HOME: "the global skill dirs",
}


def pick_root(amb: AmbiguousRoot) -> Root:
    """Let the user disambiguate a dest path instead of deciding silently."""
    _ensure_tty()
    choices = [
        questionary.Choice(title=f"{_ROOT_LABEL[r.kind]}  ({r.path})", value=r)
        for r in amb.roots
    ]
    return _ask(
        questionary.select(f"{amb.path} is ambiguous — install where?", choices=choices)
    )


def pick_products(cands: list[Dest]) -> list[Dest]:
    """Checkbox over the product conventions available at a dest root.

    Products already configured there (marker dir exists) are pre-checked.
    """
    _ensure_tty()
    choices = []
    for d in cands:
        configured = is_configured(d)
        suffix = "  (configured)" if configured else ""
        choices.append(
            questionary.Choice(
                title=f"{by_key(d.product).name}  ->  {d.skills_dir}{suffix}",
                value=d,
                checked=configured,
            )
        )
    picked = _ask(questionary.checkbox("install for which products?", choices=choices))
    if not picked:
        raise click.ClickException("nothing selected")
    return picked


def pick_method(default: Method) -> Method:
    _ensure_tty()
    choices = [questionary.Choice(title=m.value, value=m) for m in Method]
    default_choice = next(c for c in choices if c.value is default)
    return _ask(
        questionary.select("install method", choices=choices, default=default_choice)
    )


def pick_installed(items: list[tuple[Dest, str, dict]]) -> list[tuple[Dest, str]]:
    """Checkbox over installed skills across product dirs at one dest root."""
    _ensure_tty()
    choices = [
        questionary.Choice(
            title=f"[{d.product}] {name}  [{e['method']}]  from {e['skill']}",
            value=(d, name),
        )
        for d, name, e in items
    ]
    picked = _ask(
        questionary.checkbox(
            "skills to remove (space = toggle, enter = done)", choices=choices
        )
    )
    if not picked:
        raise click.ClickException("nothing selected")
    return picked
