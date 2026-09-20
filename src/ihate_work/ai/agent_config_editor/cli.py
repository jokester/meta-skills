"""Interactive editor for agent config. Run via ./agent-config.

Bare invocation opens the TUI (pick a store, then loop: add / remove /
switch / quit). `list` and `remove` are also scriptable subcommands.
Claude only, for now — the store layer (claude_config.py) is the part a
second product would need to generalize.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import click
import questionary

from ihate_work.ai.meta_skills.errors import MetaSkillsError
from ihate_work.ai.meta_skills.tui import _ask, _ensure_tty

from . import claude_config as cc


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Manage Claude MCP servers (repo .mcp.json / user ~/.claude.json)."""
    if ctx.invoked_subcommand is None:
        _menu()


def _store(scope: str) -> cc.Store:
    try:
        return cc.repo_store(Path.cwd()) if scope == "repo" else cc.user_store()
    except MetaSkillsError as e:
        raise click.ClickException(str(e))


def _available_stores() -> list[cc.Store]:
    stores = [cc.user_store()]
    try:
        stores.insert(0, cc.repo_store(Path.cwd()))
    except MetaSkillsError:
        pass  # cwd not in a repo: user scope only
    return stores


def _print_servers(store: cc.Store, servers: dict[str, dict]) -> None:
    click.secho(store.label, bold=True)
    if not servers:
        click.echo("  (no mcp servers)")
    for name, s in sorted(servers.items()):
        click.echo(f"  {name}  {cc.describe(s)}")


@cli.command("list")
@click.option("--scope", type=click.Choice(cc.SCOPES), default=None)
def list_(scope: str | None) -> None:
    """Show configured MCP servers (default: every applicable scope)."""
    stores = [_store(scope)] if scope else _available_stores()
    for store in stores:
        try:
            _print_servers(store, cc.load_servers(store))
        except MetaSkillsError as e:
            click.secho(f"  ! {e}", fg="red")


@cli.command("remove")
@click.argument("names", nargs=-1, required=True)
@click.option("--scope", type=click.Choice(cc.SCOPES), required=True)
@click.option("--yes", is_flag=True, help="skip confirmation")
def remove_(names: tuple[str, ...], scope: str, yes: bool) -> None:
    """Remove MCP servers by name from --scope."""
    store = _store(scope)
    try:
        servers = cc.load_servers(store)
        missing = sorted(set(names) - set(servers))
        if missing:
            raise MetaSkillsError(
                f"not configured in {store.path}: {', '.join(missing)}"
            )
        for n in names:
            click.echo(f"  will remove {n} from {store.path}")
        if not (yes or click.confirm("proceed?", default=False)):
            raise click.Abort()
        for n in names:
            servers.pop(n)
        cc.save_servers(store, servers)
    except MetaSkillsError as e:
        raise click.ClickException(str(e))
    click.secho(
        f"removed {', '.join(names)} (backup: {store.path.name}{cc.BACKUP_SUFFIX})",
        fg="green",
    )


# --- the TUI ------------------------------------------------------------


def _menu() -> None:
    _ensure_tty()
    store = _pick_store()
    while True:
        try:
            servers = cc.load_servers(store)
        except MetaSkillsError as e:
            click.secho(str(e), fg="red")
            store = _pick_store()
            continue
        _print_servers(store, servers)
        action = _ask(
            questionary.select(
                "action",
                choices=["add a server", "remove servers", "switch scope", "quit"],
            )
        )
        try:
            if action == "add a server":
                _add_flow(store, servers)
            elif action == "remove servers":
                _remove_flow(store, servers)
            elif action == "switch scope":
                store = _pick_store()
            else:
                return
        except MetaSkillsError as e:
            click.secho(str(e), fg="red")


def _pick_store() -> cc.Store:
    stores = _available_stores()
    if len(stores) == 1:
        click.echo(f"(cwd not in a git repo — {stores[0].label} only)")
        return stores[0]
    choices = [questionary.Choice(title=s.label, value=s) for s in stores]
    return _ask(questionary.select("which config?", choices=choices))


def _add_flow(store: cc.Store, servers: dict[str, dict]) -> None:
    name = _ask(questionary.text("server name")).strip()
    if name in servers:
        raise MetaSkillsError(f"{name!r} already exists (remove it first)")
    transport = _ask(questionary.select("transport", choices=["stdio", "http", "sse"]))

    server: dict = {"type": transport}
    if transport == "stdio":
        argv = shlex.split(_ask(questionary.text("command (with args)")))
        if not argv:
            raise MetaSkillsError("empty command")
        server["command"] = argv[0]
        if argv[1:]:
            server["args"] = argv[1:]
        env = _kv_pairs("env")
        if env:
            server["env"] = env
    else:
        server["url"] = _ask(questionary.text("url")).strip()
        headers = _kv_pairs("header")
        if headers:
            server["headers"] = headers

    cc.validate(name, server)
    click.echo(f"  {name}  {cc.describe(server)}")
    if not _ask(questionary.confirm(f"add to {store.path}?", default=True)):
        return
    cc.save_servers(store, {**servers, name: server})
    click.secho(f"added {name}", fg="green")


def _remove_flow(store: cc.Store, servers: dict[str, dict]) -> None:
    if not servers:
        raise MetaSkillsError("nothing to remove")
    choices = [
        questionary.Choice(title=f"{n}  {cc.describe(s)}", value=n)
        for n, s in sorted(servers.items())
    ]
    picked = _ask(questionary.checkbox("remove which?", choices=choices))
    if not picked:
        return
    if not _ask(
        questionary.confirm(f"remove {len(picked)} from {store.path}?", default=False)
    ):
        return
    remaining = {n: s for n, s in servers.items() if n not in picked}
    cc.save_servers(store, remaining)
    click.secho(f"removed {', '.join(picked)}", fg="green")


def _kv_pairs(what: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    while True:
        raw = _ask(questionary.text(f"{what} KEY=VALUE (empty to finish)")).strip()
        if not raw:
            return pairs
        key, sep, value = raw.partition("=")
        if not sep or not key.strip():
            click.secho("  expected KEY=VALUE", fg="yellow")
            continue
        pairs[key.strip()] = value


def main() -> int:
    cli(prog_name="agent-config")
    return 0


if __name__ == "__main__":
    sys.exit(main())
