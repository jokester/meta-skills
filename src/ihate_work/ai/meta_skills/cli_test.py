"""End-to-end tests of the scripted (non-TUI) CLI paths."""

import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from ihate_work.ai.meta_skills import discover
from ihate_work.ai.meta_skills.cli import cli


@pytest.fixture
def dest_repo(tmp_path: Path) -> Path:
    root = tmp_path / "dest-repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_list_runs():
    r = CliRunner().invoke(cli, ["list"])
    assert r.exit_code == 0, r.output
    assert "my" in r.output


def test_scripted_install_status_uninstall(dest_repo: Path):
    # pick any real skill from this repo, so the test doesn't pin a name
    skill = discover.all_skills()[0]
    runner = CliRunner()

    r = runner.invoke(
        cli,
        [
            "install",
            skill.id,
            "--dest",
            str(dest_repo),
            "--product",
            "codex",
            "--method",
            "copy",
            "--yes",
        ],
    )
    assert r.exit_code == 0, r.output
    installed = dest_repo / ".codex" / "skills" / skill.name
    assert (installed / "SKILL.md").is_file()

    # .codex now exists -> the single configured product, no flag needed
    r = runner.invoke(cli, ["status", "--dest", str(dest_repo)])
    assert r.exit_code == 0, r.output
    assert skill.name in r.output and "codex" in r.output and "ok" in r.output

    r = runner.invoke(cli, ["uninstall", skill.name, "--dest", str(dest_repo), "--yes"])
    assert r.exit_code == 0, r.output
    assert not installed.exists()


def test_scripted_bare_repo_needs_product(dest_repo: Path):
    skill = discover.all_skills()[0]
    r = CliRunner().invoke(
        cli, ["install", skill.id, "--dest", str(dest_repo), "--yes"]
    )
    assert r.exit_code != 0
    assert "--product" in r.output
    assert not any(dest_repo.glob(".*/skills"))  # nothing installed silently


def test_scripted_single_configured_product_is_used(dest_repo: Path):
    (dest_repo / ".pi").mkdir()
    skill = discover.all_skills()[0]
    r = CliRunner().invoke(
        cli,
        ["install", skill.id, "--dest", str(dest_repo), "--method", "copy", "--yes"],
    )
    assert r.exit_code == 0, r.output
    assert (dest_repo / ".pi" / "skills" / skill.name / "SKILL.md").is_file()


def test_scripted_ambiguous_dest_fails_loudly(dest_repo: Path):
    sub = dest_repo / "test"
    sub.mkdir()
    skill = discover.all_skills()[0]
    r = CliRunner().invoke(cli, ["install", skill.id, "--dest", str(sub), "--yes"])
    assert r.exit_code != 0
    assert "ambiguous" in r.output
    assert not (dest_repo / ".claude").exists()  # nothing installed silently


def test_wizard_refuses_without_tty():
    # CliRunner's stdin is not a TTY, so bare `install` must fail cleanly
    r = CliRunner().invoke(cli, ["install"])
    assert r.exit_code != 0
    assert "needs a TTY" in r.output
