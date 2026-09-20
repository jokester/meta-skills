"""Extraction engine tests.

All of these run against a synthetic upstream tree: the point is the
stages, not any particular upstream. `fetch()` is the one part these do
not cover — it is git-over-network, exercised by actually running
`./cli extract`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ihate_work.ai.meta_skills import extract
from ihate_work.ai.meta_skills.errors import MetaSkillsError
from ihate_work.ai.meta_skills.recipes import Recipe, Root

REV = "0" * 40


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def bundle(root: Path, name: str, *, fm: str = "", body: str = "body text") -> Path:
    d = root / name
    write(d / "SKILL.md", f"---\nname: {name}\n{fm}---\n{body}\n")
    return d


@pytest.fixture
def upstream(tmp_path: Path) -> Path:
    """A miniature of the shape the recipe expects."""
    src = tmp_path / "upstream"
    write(src / "LICENSE", "Apache License 2.0\n")
    for i in range(3):
        bundle(src / "skills", f"skill-{i}")
    for i in range(2):
        bundle(src / "design-templates", f"tpl-{i}")
    write(src / "craft" / "typography.md", "# typography\n")
    return src


@pytest.fixture
def recipe() -> Recipe:
    return Recipe(
        collection="acme/things",
        url="https://example.invalid/acme/things",
        rev=REV,
        summary="test recipe",
        roots=(Root("skills", 1), Root("design-templates", 1)),
        craft_dir="craft",
    )


def run_stages(
    recipe: Recipe, src: Path, staging: Path, extra_names: set[str] = frozenset()
) -> extract.Result:
    """collect -> filter -> stage -> normalize -> enrich, without git."""
    staging.mkdir(parents=True, exist_ok=True)
    result = extract.Result(collection=recipe.collection, rev=recipe.rev, out=staging)
    bundles = extract.filter_bundles(recipe, extract.collect(recipe, src), result)
    result.kept = sorted(b.name for b in bundles)
    extract.stage(bundles, staging)
    extract.normalize(bundles, staging, result)
    extract.enrich(recipe, bundles, src, staging, result, extra_names)
    return result


# --- frontmatter -------------------------------------------------------


def test_set_scalar_replaces_a_block_scalar_wholesale():
    fm = "name: old\ndescription: |\n  line one\n  line two\ntriggers:\n  - a\n"
    out = extract.set_scalar(fm, "description", "short")
    assert extract.parse_meta(out) == {
        "name": "old",
        "description": "short",
        "triggers": ["a"],
    }


def test_set_scalar_leaves_every_other_line_byte_identical():
    fm = 'name: old\nzh_description: "杂志风"\ntriggers:\n  - "杂志风 PPT"\n'
    out = extract.set_scalar(fm, "name", "new")
    assert out.splitlines()[1:] == fm.splitlines()[1:]


def test_set_scalar_prepends_a_missing_key():
    assert extract.set_scalar("other: 1", "name", "x").startswith("name: x\n")


def test_parse_meta_survives_unparseable_frontmatter():
    assert extract.parse_meta("name: [unclosed\n") == {}


# --- collect / filter --------------------------------------------------


def test_collect_fails_loudly_when_a_root_is_gone(recipe, upstream, tmp_path):
    (upstream / "skills").rename(tmp_path / "moved")
    with pytest.raises(MetaSkillsError, match="no skills/"):
        extract.collect(recipe, upstream)


def test_collect_fails_loudly_when_a_root_shrinks(upstream):
    picky = Recipe(
        collection="acme/things",
        url="u",
        rev=REV,
        summary="s",
        roots=(Root("skills", 99),),
    )
    with pytest.raises(MetaSkillsError, match="expected at least 99"):
        extract.collect(picky, upstream)


def test_stubs_and_denylisted_dirs_are_dropped_with_a_reason(upstream, tmp_path):
    bundle(upstream / "skills", "stubby", body="this is a POINTER ONLY entry")
    r = Recipe(
        collection="acme/things",
        url="u",
        rev=REV,
        summary="s",
        roots=(Root("skills", 1),),
        drop_dirs=frozenset({"skill-0"}),
        stub_marker="POINTER ONLY",
    )
    result = run_stages(r, upstream, tmp_path / "staging")
    assert result.kept == ["skill-1", "skill-2"]
    assert result.drops_by_reason == {
        "denylisted by the recipe": ["skill-0"],
        "catalogue stub: frontmatter only, no workflow": ["stubby"],
    }


def test_a_bundle_relying_on_a_dropped_stub_is_dropped_too(upstream, tmp_path):
    bundle(upstream / "skills", "stubby", body="POINTER ONLY, nothing here")
    bundle(upstream / "skills", "needs-stub", body="see [base](../stubby/SKILL.md)")
    bundle(upstream / "skills", "needs-needs", body="see [x](../needs-stub/SKILL.md)")
    r = Recipe(
        collection="acme/things",
        url="u",
        rev=REV,
        summary="s",
        roots=(Root("skills", 1),),
        stub_marker="POINTER ONLY",
    )
    result = run_stages(r, upstream, tmp_path / "staging")
    # the cascade runs to a fixpoint, not just one level
    assert "needs-stub" not in result.kept
    assert "needs-needs" not in result.kept
    assert {w for n, _r, w in result.dropped if n == "needs-needs"} == {
        "relies on dropped stub needs-stub"
    }


def test_a_bundle_mentioning_a_denylisted_one_survives_with_the_link_defused(
    upstream, tmp_path
):
    bundle(upstream / "skills", "mentions", body="see [heavy](../skill-0/assets/x.png)")
    r = Recipe(
        collection="acme/things",
        url="u",
        rev=REV,
        summary="s",
        roots=(Root("skills", 1),),
        drop_dirs=frozenset({"skill-0"}),
    )
    staging = tmp_path / "staging"
    result = run_stages(r, upstream, staging)
    # denylisting is our weight call, not a statement that the referrer is bad
    assert "mentions" in result.kept
    _fm, body = extract.split_frontmatter(
        (staging / "mentions" / "SKILL.md").read_text()
    )
    assert "[heavy](" not in body
    assert "not bundled in this extract" in body
    assert result.neutralized == [("mentions", ["../skill-0/assets/x.png"])]


def test_an_escape_out_of_the_collection_is_not_read_as_a_sibling(
    upstream, tmp_path, recipe
):
    bundle(upstream / "skills", "escapes", body="[d](../../design-systems/k/D.md)")
    result = run_stages(recipe, upstream, tmp_path / "staging")
    # `../..` is not a bundle named `..`; mistaking it for one drops good work
    assert "escapes" in result.kept


def test_recipe_link_rewrites_are_applied_before_anything_is_defused(
    upstream, tmp_path
):
    bundle(upstream / "skills", "escapes", body="[d](../../design-systems/k/D.md)")
    r = Recipe(
        collection="acme/things",
        url="u",
        rev=REV,
        summary="s",
        roots=(Root("skills", 1),),
        link_rewrites=((r"\]\(\.\./\.\./design-systems/", "](../router/references/"),),
    )
    staging = tmp_path / "staging"
    result = run_stages(r, upstream, staging, extra_names={"router"})
    text = (staging / "escapes" / "SKILL.md").read_text()
    assert "[d](../router/references/k/D.md)" in text
    assert result.neutralized == []


def test_a_sibling_reference_that_survives_keeps_its_referrer(upstream, tmp_path):
    bundle(upstream / "skills", "needs-one", body="see [base](../skill-1/SKILL.md)")
    result = run_stages(
        Recipe(
            collection="acme/things",
            url="u",
            rev=REV,
            summary="s",
            roots=(Root("skills", 1),),
        ),
        upstream,
        tmp_path / "staging",
    )
    assert "needs-one" in result.kept


# --- normalize / enrich ------------------------------------------------


def test_name_is_moved_to_match_the_directory(upstream, tmp_path, recipe):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: something-else\ndescription: d\n---\nbody\n",
    )
    staging = tmp_path / "staging"
    result = run_stages(recipe, upstream, staging)
    fm, _ = extract.split_frontmatter((staging / "skill-0" / "SKILL.md").read_text())
    assert extract.parse_meta(fm)["name"] == "skill-0"
    assert ("skill-0", "something-else") in result.renamed


def test_the_directory_is_never_renamed_because_siblings_point_at_it(
    upstream, tmp_path, recipe
):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: something-else\ndescription: d\n---\nbody\n",
    )
    bundle(upstream / "skills", "referrer", body="[b](../skill-0/SKILL.md)")
    staging = tmp_path / "staging"
    run_stages(recipe, upstream, staging)
    assert (staging / "skill-0").is_dir()
    assert "[b](../skill-0/SKILL.md)" in (staging / "referrer" / "SKILL.md").read_text()


def test_a_missing_description_is_synthesized_from_the_body(upstream, tmp_path, recipe):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: skill-0\n---\n# Heading\n\nWhat it actually does.\n",
    )
    staging = tmp_path / "staging"
    result = run_stages(recipe, upstream, staging)
    fm, _ = extract.split_frontmatter((staging / "skill-0" / "SKILL.md").read_text())
    assert extract.parse_meta(fm)["description"] == "What it actually does."
    assert "skill-0" in result.described


def test_craft_references_are_inlined_as_files_and_announced(
    upstream, tmp_path, recipe
):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: skill-0\ndescription: d\n"
        "od:\n  craft:\n    requires: [typography]\n---\nbody\n",
    )
    staging = tmp_path / "staging"
    result = run_stages(recipe, upstream, staging)
    assert (staging / "skill-0" / "references" / "craft" / "typography.md").is_file()
    assert (
        "references/craft/typography.md"
        in (staging / "skill-0" / "SKILL.md").read_text()
    )
    assert result.crafted == [("skill-0", ["typography"])]


def test_a_missing_craft_reference_warns_instead_of_failing(upstream, tmp_path, recipe):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: skill-0\ndescription: d\n"
        "od:\n  craft:\n    requires: [nope]\n---\nbody\n",
    )
    result = run_stages(recipe, upstream, tmp_path / "staging")
    assert any("no craft reference nope.md" in w for w in result.warnings)


def test_repo_root_links_become_sibling_links(upstream, tmp_path, recipe):
    bundle(
        upstream / "skills",
        "linker",
        body="see [t](design-templates/tpl-0/SKILL.md) and [u](skills/skill-1/SKILL.md)",
    )
    staging = tmp_path / "staging"
    result = run_stages(recipe, upstream, staging)
    text = (staging / "linker" / "SKILL.md").read_text()
    assert "[t](../tpl-0/SKILL.md)" in text
    assert "[u](../skill-1/SKILL.md)" in text
    assert "linker" in result.relinked


def test_a_repo_root_link_to_something_we_dropped_is_left_alone(
    upstream, tmp_path, recipe
):
    bundle(upstream / "skills", "linker", body="[gone](skills/not-extracted/SKILL.md)")
    staging = tmp_path / "staging"
    run_stages(recipe, upstream, staging)
    text = (staging / "linker" / "SKILL.md").read_text()
    assert "[gone](skills/not-extracted/SKILL.md)" in text


# --- verify ------------------------------------------------------------


def test_verify_rejects_a_bundle_whose_name_drifted(tmp_path):
    staging = tmp_path / "staging"
    bundle(staging, "good", fm="description: d\n")
    write(staging / "bad" / "SKILL.md", "---\nname: other\ndescription: d\n---\nb\n")
    with pytest.raises(MetaSkillsError, match="declaring name='other'"):
        extract.verify(staging, extract.Result("c", REV, staging))


def test_verify_rejects_a_bundle_with_no_description(tmp_path):
    staging = tmp_path / "staging"
    bundle(staging, "bare")
    with pytest.raises(MetaSkillsError, match="without a description"):
        extract.verify(staging, extract.Result("c", REV, staging))


def test_verify_only_warns_about_a_dangling_sibling_link(tmp_path):
    staging = tmp_path / "staging"
    bundle(staging, "one", fm="description: d\n", body="[x](../missing/SKILL.md)")
    result = extract.Result("c", REV, staging)
    extract.verify(staging, result)
    assert result.warnings == ["one: dangling sibling reference ../missing"]


# --- attribution & publication -----------------------------------------


def test_attribution_records_the_pin_and_what_we_changed(upstream, tmp_path, recipe):
    write(
        upstream / "skills" / "skill-0" / "SKILL.md",
        "---\nname: elsewhere\ndescription: d\n"
        "od:\n  upstream: https://example.invalid/orig\n---\nbody\n",
    )
    staging = tmp_path / "staging"
    result = run_stages(recipe, upstream, staging)
    extract.attribute(recipe, upstream, staging, result)
    text = (staging / "skill-0" / "ATTRIBUTION.md").read_text()
    assert recipe.rev in text
    assert "https://example.invalid/orig" in text
    assert "was `elsewhere`" in text
    assert (staging / "LICENSE").is_file()


def test_run_publishes_atomically_and_records_state(
    monkeypatch, upstream, tmp_path, recipe
):
    repo = tmp_path / "repo"
    cache = extract.cache_dir(repo, recipe.collection)
    cache.parent.mkdir(parents=True)
    # stand in for fetch(): a cache that is already at the pinned rev
    import shutil

    shutil.copytree(upstream, cache)
    (cache / ".git").mkdir()
    monkeypatch.setattr(extract, "_git", lambda *a, **k: recipe.rev)

    result = extract.run(recipe, repo, do_fetch=False)

    out = extract.build_dir(repo, recipe.collection)
    assert out.is_dir() and not (out.parent / f".staging-{out.name}").exists()
    assert sorted(p.name for p in out.iterdir() if p.is_dir()) == result.kept
    state = json.loads((out / extract.STATE_NAME).read_text())
    assert state["rev"] == recipe.rev
    assert extract.state_of(repo, recipe.collection) == state
    assert not extract.is_stale(repo, recipe)


def test_run_leaves_no_staging_dir_behind_when_a_stage_fails(
    monkeypatch, upstream, tmp_path, recipe
):
    repo = tmp_path / "repo"
    cache = extract.cache_dir(repo, recipe.collection)
    cache.parent.mkdir(parents=True)
    import shutil

    shutil.copytree(upstream, cache)
    (cache / ".git").mkdir()
    monkeypatch.setattr(extract, "_git", lambda *a, **k: recipe.rev)
    monkeypatch.setattr(
        extract, "verify", lambda *a: (_ for _ in ()).throw(MetaSkillsError("nope"))
    )

    with pytest.raises(MetaSkillsError, match="nope"):
        extract.run(recipe, repo, do_fetch=False)
    out = extract.build_dir(repo, recipe.collection)
    assert not out.exists()
    assert not (out.parent / f".staging-{out.name}").exists()


def test_run_refuses_a_cache_that_is_not_at_the_pin(
    monkeypatch, upstream, tmp_path, recipe
):
    repo = tmp_path / "repo"
    cache = extract.cache_dir(repo, recipe.collection)
    cache.parent.mkdir(parents=True)
    import shutil

    shutil.copytree(upstream, cache)
    (cache / ".git").mkdir()
    monkeypatch.setattr(extract, "_git", lambda *a, **k: "f" * 40)
    with pytest.raises(MetaSkillsError, match="recipe pins"):
        extract.run(recipe, repo, do_fetch=False)


def test_installing_from_a_stale_extract_is_refused(monkeypatch, tmp_path):
    """The recorded rev comes from the recipe, so a stale build must not install."""
    from ihate_work.ai.meta_skills import install
    from ihate_work.ai.meta_skills.model import (
        Dest,
        DestKind,
        Method,
        Skill,
        SourceKind,
    )

    recipe = Recipe(collection="acme/things", url="u", rev=REV, summary="s")
    monkeypatch.setattr("ihate_work.ai.meta_skills.recipes.get", lambda c: recipe)
    monkeypatch.setattr(extract, "is_stale", lambda _root, _recipe: True)
    skill = Skill(
        name="one",
        path=tmp_path / "one",
        source=SourceKind.REMOTE,
        collection="acme/things",
    )
    dest = Dest(
        kind=DestKind.DIR,
        root=tmp_path,
        skills_dir=tmp_path / ".claude" / "skills",
        product="claude",
    )
    with pytest.raises(MetaSkillsError, match="extracted at an older pin"):
        install.plan(skill, dest, Method.COPY)
