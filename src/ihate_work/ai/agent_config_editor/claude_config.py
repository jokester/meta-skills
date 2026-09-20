"""Read/write Claude's MCP server config stores.

Claude Code keeps MCP servers in two places we manage:

- repo scope: `<repo>/.mcp.json`, top-level `mcpServers` (committed, shared)
- user scope: `~/.claude.json`, top-level `mcpServers` (this machine)

(A third "local" scope lives inside ~/.claude.json's `projects` section;
not managed yet.)

Writes follow the meta_skills safety rules: nothing is mutated unless the
whole write will succeed — read + validate first, back up, then atomic
replace — and every key in the file other than `mcpServers` is preserved
untouched (~/.claude.json holds a lot of unrelated Claude state).
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from ihate_work.ai.meta_skills.errors import MetaSkillsError
from ihate_work.ai.meta_skills.gitutil import repo_root_of

BACKUP_SUFFIX = ".bak-agent-config-editor"
SCOPES = ["repo", "user"]


@dataclass(frozen=True)
class Store:
    scope: str  # "repo" | "user"
    path: Path

    @property
    def label(self) -> str:
        return f"{self.scope}: {self.path}"


def user_store() -> Store:
    return Store("user", Path.home() / ".claude.json")


def repo_store(start: Path) -> Store:
    root = repo_root_of(start)
    if root is None:
        raise MetaSkillsError(f"{start} is not inside a git repo")
    return Store("repo", root / ".mcp.json")


def _load_doc(store: Store) -> dict:
    if not store.path.is_file():
        return {}
    try:
        doc = json.loads(store.path.read_text())
    except json.JSONDecodeError as e:
        # unlike our own manifests, these files are NOT ours to quarantine
        raise MetaSkillsError(
            f"{store.path} is not valid JSON ({e}) — refusing to touch it, fix by hand"
        ) from e
    if not isinstance(doc, dict):
        raise MetaSkillsError(f"{store.path}: expected a JSON object")
    return doc


def load_servers(store: Store) -> dict[str, dict]:
    servers = _load_doc(store).get("mcpServers", {})
    if not isinstance(servers, dict):
        raise MetaSkillsError(f"{store.path}: mcpServers is not an object")
    return servers


def save_servers(store: Store, servers: dict[str, dict]) -> None:
    """Replace mcpServers, preserving every other key in the file."""
    doc = _load_doc(store)  # validates the current file before any mutation
    doc["mcpServers"] = servers
    if store.path.is_file():
        shutil.copy2(store.path, store.path.with_name(store.path.name + BACKUP_SUFFIX))
    tmp = store.path.with_name(store.path.name + ".tmp-agent-config-editor")
    tmp.write_text(json.dumps(doc, indent=2) + "\n")
    os.replace(tmp, store.path)


def validate(name: str, server: dict) -> None:
    """Raise unless (name, server) is a Claude-acceptable MCP entry."""
    if not name or any(c.isspace() for c in name):
        raise MetaSkillsError(f"bad server name: {name!r}")
    t = server.get("type", "stdio")
    if t == "stdio" and not server.get("command"):
        raise MetaSkillsError("a stdio server needs a command")
    if t in ("http", "sse") and not str(server.get("url", "")).startswith(
        ("http://", "https://")
    ):
        raise MetaSkillsError(f"an {t} server needs an http(s) url")


def describe(server: dict) -> str:
    """One-line summary of a server entry."""
    t = server.get("type", "stdio" if "command" in server else "?")
    if "command" in server:
        return f"[{t}] " + " ".join([server["command"], *server.get("args", [])])
    if "url" in server:
        return f"[{t}] {server['url']}"
    return f"[{t}]"
