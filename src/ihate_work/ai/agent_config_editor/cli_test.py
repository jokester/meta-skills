"""End-to-end tests of the scriptable (non-TUI) paths."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from ihate_work.ai.agent_config_editor import claude_config as cc
from ihate_work.ai.agent_config_editor.cli import cli


@pytest.fixture
def user_file(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    p = tmp_path / ".claude.json"
    p.write_text(
        json.dumps(
            {
                "someOtherState": 1,
                "mcpServers": {
                    "github": {"type": "http", "url": "https://api.example/mcp"},
                    "local-fs": {"command": "npx", "args": ["-y", "fs-server"]},
                },
            }
        )
    )
    return p


def test_list(user_file: Path):
    r = CliRunner().invoke(cli, ["list", "--scope", "user"])
    assert r.exit_code == 0, r.output
    assert "github" in r.output and "https://api.example/mcp" in r.output
    assert "local-fs" in r.output and "[stdio] npx -y fs-server" in r.output


def test_remove(user_file: Path):
    r = CliRunner().invoke(cli, ["remove", "github", "--scope", "user", "--yes"])
    assert r.exit_code == 0, r.output
    doc = json.loads(user_file.read_text())
    assert list(doc["mcpServers"]) == ["local-fs"]
    assert doc["someOtherState"] == 1
    assert user_file.with_name(user_file.name + cc.BACKUP_SUFFIX).is_file()


def test_remove_unknown_is_clean(user_file: Path):
    r = CliRunner().invoke(cli, ["remove", "nope", "--scope", "user", "--yes"])
    assert r.exit_code != 0
    assert "not configured" in r.output and "Traceback" not in r.output


def test_tui_refuses_without_tty(user_file: Path):
    r = CliRunner().invoke(cli, [])
    assert r.exit_code != 0
    assert "needs a TTY" in r.output
