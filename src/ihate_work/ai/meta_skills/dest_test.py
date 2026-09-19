import subprocess
from pathlib import Path

import pytest

from ihate_work.ai.meta_skills import dest
from ihate_work.ai.meta_skills.model import DestKind


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_repo_dest(tmp_path: Path):
    _git_init(tmp_path)
    sub = tmp_path / "some" / "subdir"
    sub.mkdir(parents=True)

    d = dest.resolve(sub)
    assert d.kind is DestKind.REPO
    assert d.root == tmp_path.resolve()
    assert d.skills_dir == tmp_path.resolve() / ".claude" / "skills"


def test_dir_dest(tmp_path: Path):
    (tmp_path / ".claude").mkdir()
    d = dest.resolve(tmp_path)
    assert d.kind is DestKind.DIR
    assert d.skills_dir == tmp_path.resolve() / ".claude" / "skills"


def test_unrecognizable_dest(tmp_path: Path):
    with pytest.raises(ValueError, match="not a recognizable dest"):
        dest.resolve(tmp_path)


def test_missing_dir(tmp_path: Path):
    with pytest.raises(ValueError, match="not a directory"):
        dest.resolve(tmp_path / "nope")
