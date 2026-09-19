from pathlib import Path

from ihate_work.ai.meta_skills import discover
from ihate_work.ai.meta_skills.model import SourceKind


def _mk_skill(root: Path, *parts: str) -> Path:
    d = root.joinpath(*parts)
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("# skill\n")
    return d


def test_discover_own_skills(tmp_path: Path):
    _mk_skill(tmp_path, "my", "foo")
    _mk_skill(tmp_path, "my", "nested", "bar")

    cols = discover.discover(tmp_path)
    my = next(c for c in cols if c.name == "my")
    assert my.source is SourceKind.OWN
    assert [s.name for s in my.skills] == ["foo", "bar"]  # sorted by path
    assert my.skills[0].id == "my/foo"


def test_hidden_dirs_pruned(tmp_path: Path):
    _mk_skill(tmp_path, "my", ".hidden", "foo")
    assert discover.all_skills(tmp_path) == []


def test_find_skill_exact_beats_substring(tmp_path: Path):
    _mk_skill(tmp_path, "my", "foo")
    _mk_skill(tmp_path, "my", "foo-extra")

    assert [s.id for s in discover.find_skill("foo", tmp_path)] == ["my/foo"]
    assert len(discover.find_skill("fo", tmp_path)) == 2


def test_real_repo_lists_submodule_collections():
    names = {c.name for c in discover.discover()}
    assert "my" in names
    assert "obra/superpowers" in names
