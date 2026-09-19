import subprocess
from pathlib import Path

import pytest

from ihate_work.ai.meta_skills import install, manifest
from ihate_work.ai.meta_skills.model import Dest, DestKind, Method, Skill, SourceKind


@pytest.fixture
def skill(tmp_path: Path) -> Skill:
    d = tmp_path / "src-skills" / "foo"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# foo\n")
    return Skill(name="foo", path=d, source=SourceKind.OWN, collection="my")


@pytest.fixture
def repo_dest(tmp_path: Path) -> Dest:
    root = (tmp_path / "dest-repo").resolve()
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return Dest(
        kind=DestKind.REPO,
        root=root,
        skills_dir=root / ".claude" / "skills",
        product="claude",
    )


def test_copy_into_repo(skill: Skill, repo_dest):
    p = install.plan(skill, repo_dest, Method.COPY)
    assert p.warnings == ()

    target = install.execute(p)
    assert (target / "SKILL.md").is_file()
    assert not target.is_symlink()

    entry = manifest.load(repo_dest.skills_dir)["foo"]
    assert entry["skill"] == "my/foo"
    assert entry["method"] == "copy"
    assert entry["source_rev"]  # this repo's HEAD


def test_symlink_into_repo_warns_and_gitignores(skill: Skill, repo_dest):
    p = install.plan(skill, repo_dest, Method.SYMLINK)
    assert any("REPO & SYMLINK" in w for w in p.warnings)

    target = install.execute(p)
    assert target.is_symlink() and (target / "SKILL.md").is_file()
    assert "/.claude/skills/foo" in (repo_dest.root / ".gitignore").read_text()


def test_existing_target_needs_force(skill: Skill, repo_dest):
    install.execute(install.plan(skill, repo_dest, Method.COPY))
    with pytest.raises(FileExistsError):
        install.execute(install.plan(skill, repo_dest, Method.COPY))
    install.execute(install.plan(skill, repo_dest, Method.SYMLINK), force=True)
    assert (repo_dest.skills_dir / "foo").is_symlink()


def test_uninstall(skill: Skill, repo_dest):
    install.execute(install.plan(skill, repo_dest, Method.COPY))
    install.uninstall(repo_dest, "foo")
    assert not (repo_dest.skills_dir / "foo").exists()
    assert manifest.load(repo_dest.skills_dir) == {}


def test_custom_without_rewiring_is_an_error(skill: Skill, repo_dest):
    with pytest.raises(ValueError, match="no rewiring registered"):
        install.plan(skill, repo_dest, Method.CUSTOM)
