import json
import subprocess
from pathlib import Path

import pytest

from ihate_work.ai.agent_config_editor import claude_config as cc
from ihate_work.ai.meta_skills.errors import MetaSkillsError


@pytest.fixture
def user(tmp_path: Path, monkeypatch) -> cc.Store:
    monkeypatch.setenv("HOME", str(tmp_path))
    return cc.user_store()


def test_missing_file_is_empty(user: cc.Store):
    assert cc.load_servers(user) == {}


def test_save_preserves_unrelated_keys_and_backs_up(user: cc.Store):
    user.path.write_text(
        json.dumps(
            {"oauthAccount": {"id": "x"}, "mcpServers": {"old": {"command": "a"}}}
        )
    )
    cc.save_servers(user, {"new": {"type": "stdio", "command": "b"}})

    doc = json.loads(user.path.read_text())
    assert doc["oauthAccount"] == {"id": "x"}  # untouched
    assert list(doc["mcpServers"]) == ["new"]
    backup = user.path.with_name(user.path.name + cc.BACKUP_SUFFIX)
    assert "old" in json.loads(backup.read_text())["mcpServers"]
    assert not list(user.path.parent.glob("*.tmp-*"))  # no temp leftover


def test_corrupt_file_is_refused_untouched(user: cc.Store):
    user.path.write_text("{not json")
    with pytest.raises(MetaSkillsError, match="refusing to touch"):
        cc.load_servers(user)
    with pytest.raises(MetaSkillsError):
        cc.save_servers(user, {})
    assert user.path.read_text() == "{not json"  # nothing mutated


def test_repo_store(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    sub = tmp_path / "deep" / "inside"
    sub.mkdir(parents=True)
    store = cc.repo_store(sub)
    assert store.path == tmp_path.resolve() / ".mcp.json"

    with pytest.raises(MetaSkillsError, match="not inside a git repo"):
        cc.repo_store(Path("/"))


@pytest.mark.parametrize(
    ("name", "server", "msg"),
    [
        ("bad name", {"command": "x"}, "bad server name"),
        ("ok", {"type": "stdio"}, "needs a command"),
        ("ok", {"type": "http", "url": "ftp://x"}, "http\\(s\\) url"),
    ],
)
def test_validate_rejects(name, server, msg):
    with pytest.raises(MetaSkillsError, match=msg):
        cc.validate(name, server)


def test_describe():
    assert (
        cc.describe({"command": "npx", "args": ["-y", "srv"]}) == "[stdio] npx -y srv"
    )
    assert cc.describe({"type": "http", "url": "https://x"}) == "[http] https://x"
