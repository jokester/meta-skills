import subprocess
from pathlib import Path

import pytest

from ihate_work.ai.meta_skills import dest
from ihate_work.ai.meta_skills.model import DestKind
from ihate_work.ai.meta_skills.products import PRODUCTS

ALL_KEYS = {p.key for p in PRODUCTS}


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_repo_root_gives_all_products(tmp_path: Path):
    _git_init(tmp_path)
    cands = dest.candidates(tmp_path)
    assert {d.product for d in cands} == ALL_KEYS
    assert all(d.kind is DestKind.REPO and d.root == tmp_path.resolve() for d in cands)
    claude = next(d for d in cands if d.product == "claude")
    assert claude.skills_dir == tmp_path.resolve() / ".claude" / "skills"
    codex = next(d for d in cands if d.product == "codex")
    assert codex.skills_dir == tmp_path.resolve() / ".codex" / "skills"


def test_subdir_of_repo_is_ambiguous(tmp_path: Path):
    _git_init(tmp_path)
    sub = tmp_path / "some" / "subdir"
    sub.mkdir(parents=True)

    with pytest.raises(dest.AmbiguousRoot) as exc:
        dest.candidates(sub)
    kinds = [r.kind for r in exc.value.roots]
    assert kinds == [DestKind.REPO, DestKind.DIR]
    assert exc.value.roots[0].path == tmp_path.resolve()
    assert exc.value.roots[1].path == sub.resolve()


def test_marked_subdir_of_repo_is_dir(tmp_path: Path):
    _git_init(tmp_path)
    sub = tmp_path / "subproject"
    (sub / ".codex").mkdir(parents=True)

    cands = dest.candidates(sub)
    assert all(d.kind is DestKind.DIR and d.root == sub.resolve() for d in cands)
    codex = next(d for d in cands if d.product == "codex")
    assert dest.is_configured(codex)
    pi = next(d for d in cands if d.product == "pi")
    assert not dest.is_configured(pi)


def test_home_gives_all_products():
    cands = dest.candidates(Path.home())
    assert {d.product for d in cands} == ALL_KEYS
    assert all(d.kind is DestKind.HOME for d in cands)
    omp = next(d for d in cands if d.product == "omp")
    assert omp.skills_dir == Path("~/.omp/agent/skills").expanduser()


def test_product_global_dir_is_specific():
    # ~/.claude/skills and its parent ~/.claude both pin the product
    for raw in ("~/.claude/skills", "~/.claude"):
        p = Path(raw).expanduser()
        if not p.is_dir():
            pytest.skip(f"{raw} does not exist on this machine")
        (cand,) = dest.candidates(p)
        assert cand.kind is DestKind.HOME
        assert cand.product == "claude"


def test_unrecognizable_dest(tmp_path: Path):
    with pytest.raises(ValueError, match="not a recognizable dest"):
        dest.candidates(tmp_path)


def test_missing_dir(tmp_path: Path):
    with pytest.raises(ValueError, match="not a directory"):
        dest.candidates(tmp_path / "nope")
