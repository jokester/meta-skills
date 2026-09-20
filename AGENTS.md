# meta-skills

This repo is my personal skill storage & manager: a monorepo that collects
agent skills (mine and other people's) and provides tooling to install them
into the places agents look for them.

Docs split:

- `docs/SPEC.md` — the product spec: model, rules, use cases. **What** the
  manager does; change it when behavior changes.
- `docs/skill-dirs.md` — survey of per-product skill dir conventions;
  mirrored in code by `products.py`.
- `docs/external-collections.md` — how to read an upstream repo's shape and
  pick its install method, plus the resulting per-collection notes.
- this file — repo layout, code map, dev workflow. **How** it's built.

## repo layout

- `my/` — my own skills, authored in this repo (OWN).
- `<gh-username>/<repo>/` — external skill collections, vendored as git
  submodules (EXTERNAL), laid out by upstream GitHub username, e.g.
  `garrytan/gstack`, `obra/superpowers`, `mattpocock/skills`.
- `.cache/<gh-username>/<repo>/` — sparse, shallow checkouts of REMOTE
  upstreams we never vendor. Gitignored; written by `./cli extract`.
- `build/<gh-username>/<repo>/` — the installable skills extracted from
  those. Gitignored and fully derived: delete it freely, re-run `./cli
  extract` to get it back. The committed trace is `docs/extracts/`.
- `src/ihate_work/ai/meta_skills/` — the manager code (see "coding" below).
  `ihate_work` and `ihate_work.ai` are namespace packages (no `__init__.py`),
  shared with my other repos.
- `cli`, `Makefile`, `requirements.txt`, `pyproject.toml` — tooling entry
  points (see "dev workflow" below).

## the model (summary — `docs/SPEC.md` is authoritative)

An install = (skill source, dest, method): source OWN (`my/`), EXTERNAL
(submodule, pinned rev) or REMOTE (extracted from a recipe's pin into
`build/`); dest = root (HOME / REPO / DIR) × product
(`.claude`, `.codex`, `.pi`, `.omp`, `.agents` — table in `products.py`);
method COPY / SYMLINK / CUSTOM. Load-bearing rules to keep in mind while
coding: never resolve an ambiguous dest silently, never hardcode a product
convention, REPO×SYMLINK must warn + gitignore, COPY must record
provenance, CUSTOM rewiring is pinned to `(collection, rev)` and fails
loudly when stale, extraction re-checks upstream's shape and refuses to
publish a build that fails it. Details, metadata design, and use cases:
`docs/SPEC.md`.

## coding

### `ihate_work.ai.meta_skills`

The real manager: an interactive click-based CLI that installs a skill, or a
collection of skills, into a new or existing dest. Module map:

- `model.py` — the vocabulary: `SourceKind` (OWN/EXTERNAL), `DestKind`
  (HOME/REPO/DIR), `Method` (COPY/SYMLINK/CUSTOM), and the `Skill`, `Dest`,
  `InstallPlan` dataclasses.
- `errors.py` — `MetaSkillsError` for every *expected* failure (the CLI
  boundary converts exactly these to one-line messages; anything else may
  traceback — it's a bug) and `TargetExists` (CLI treats as a skip).
- `discover.py` — find skills (dirs containing `SKILL.md`) in `my/`, in
  each submodule, and in each recipe's `build/` output; collections with
  nothing in them yet still show up, carrying the hint that says what to
  run (`git submodule update --init`, or `./cli extract`).
- `products.py` — the per-product skill dir table (marker, project skills
  dir, global skills dir); kept in sync with `docs/skill-dirs.md`.
- `fsutil.py` — `remove()` and `swap()`: the stage-then-swap primitives
  every mutating path uses (installs and extractions alike).
- `recipes.py` — REMOTE collections: url, pinned rev, the sparse slice to
  fetch, and the extraction knobs (roots + their sanity floors, denylist,
  stub marker, craft dir, link rewrites, generators). Also the
  open-design design-systems router generator.
- `extract.py` — the extraction engine: fetch → collect → filter →
  normalize → enrich → generate → attribute → verify, publishing
  `build/<collection>` by one swap at the end. Frontmatter edits are line
  surgery, never a YAML round-trip.
- `dest.py` — classify a target path into per-product `Dest` candidates
  (root: HOME > REPO > DIR), raising `AmbiguousRoot` instead of walking up
  to a repo root silently.
- `install.py` — `plan()` validates a triple and collects the special-rule
  warnings; `preflight()` guarantees no mutation happens unless the install
  will succeed; `execute()` performs COPY/SYMLINK/CUSTOM via
  stage-then-swap (atomic per plan), records provenance, and maintains the
  manager-owned skills-dir `.gitignore` (symlinks + manifest transient; the
  dest repo's root .gitignore is never touched).
- `manifest.py` — `.meta-skills.json` next to installed skills: which skill,
  which method, which source rev — enables drift detection in `status`.
- `rewire.py` — registry of CUSTOM upstream adaptations, keyed by
  `(collection, upstream_rev)`; a bumped submodule makes the lookup fail
  loudly so the rewiring gets revisited.
- `gitutil.py` — thin git helpers (repo root, submodule revs) + the
  skills-dir `.gitignore` maintenance.
- `tui.py` — questionary-based interactive prompts (skill checkboxes, dest
  path, method select). TTY-only; raises cleanly without one, so scripted
  use (explicit args + `--yes`) never lands in a prompt.
- `cli.py` — click commands: `list`, `extract`, `install`, `status`,
  `uninstall`.
  `install`/`uninstall` with no positional args run the interactive wizard;
  with args they are fully scriptable.

Tests are colocated as `*_test.py` (vibra convention). Entry point is
`__main__.py`; run it via `./cli`, not by importing directly.

### `./cli`

The wrapper: ensures the venv exists (`make -s deps`), then execs
`venv/bin/python -m ihate_work.ai.meta_skills`. It preserves the caller's
cwd, so the manager can treat cwd as the default install dest.

### `ihate_work.ai.agent_config_editor`

A sibling program (wrapper: `./agent-config`): a TUI that manages agent MCP
servers. Claude only for now, two stores: repo scope `<repo>/.mcp.json`
(repo resolved from cwd) and user scope `~/.claude.json` (top-level
`mcpServers`; Claude's "local" scope inside its `projects` section is not
managed yet). It reuses meta_skills (`errors`, `tui`, `gitutil`) and its
safety rules: only the `mcpServers` key is ever touched — every other key
is preserved verbatim; writes validate first, back up to
`*.bak-agent-config-editor`, then atomically replace; a corrupt config is
refused untouched (these files are Claude's, never quarantined). Modules:

- `claude_config.py` — the store layer (locate/load/validate/save); the
  part a second product would need to generalize.
- `cli.py` — bare invocation opens the TUI loop (pick store → add /
  remove / switch / quit); `list` and `remove --scope … --yes` are
  scriptable. Adding is TUI-only for now (scripted add = edit the JSON).

## dev workflow

The venv is created and updated **only** via the Makefile (pattern copied
from vibra/py, uv-based with stamp files). Assumes `uv` is installed
globally. Never `pip install` by hand, never activate the venv manually.

- `make deps` — create/refresh `venv/` and install `requirements.txt` +
  editable self
- `make test` — run pytest over `src/` (deps implied)
- `make format-py` / `make lint-py` — ruff

Adding a dependency = edit `requirements.txt`, then `make deps`.

Adding an external skill collection = `git submodule add <url>
<gh-username>/<repo>`, then commit `.gitmodules` + the pinned rev. Before
committing, categorize it per `docs/external-collections.md` (shape → method)
and add its note there.

Adding a REMOTE collection (shape E) = write a `Recipe` in `recipes.py`
with the upstream url, a full-sha pin, the sparse slice, and each root
with a sanity floor; run `./cli extract <collection>`; commit the recipe
and the regenerated `docs/extracts/<collection>.md`. Bumping the pin is
the same loop — the report's diff is the review.
