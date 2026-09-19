# meta-skills

This repo is my personal skill storage & manager: a monorepo that collects
agent skills (mine and other people's) and provides tooling to install them
into the places agents look for them.

Docs split:

- `docs/SPEC.md` — the product spec: model, rules, use cases. **What** the
  manager does; change it when behavior changes.
- `docs/skill-dirs.md` — survey of per-product skill dir conventions;
  mirrored in code by `products.py`.
- this file — repo layout, code map, dev workflow. **How** it's built.

## repo layout

- `my/` — my own skills, authored in this repo (OWN).
- `<gh-username>/<repo>/` — external skill collections, vendored as git
  submodules (EXTERNAL), laid out by upstream GitHub username, e.g.
  `garrytan/gstack`, `obra/superpowers`, `mattpocock/skills`.
- `src/ihate_work/ai/meta_skills/` — the manager code (see "coding" below).
  `ihate_work` and `ihate_work.ai` are namespace packages (no `__init__.py`),
  shared with my other repos.
- `cli`, `Makefile`, `requirements.txt`, `pyproject.toml` — tooling entry
  points (see "dev workflow" below).

## the model (summary — `docs/SPEC.md` is authoritative)

An install = (skill source, dest, method): source OWN (`my/`) or EXTERNAL
(submodule, pinned rev); dest = root (HOME / REPO / DIR) × product
(`.claude`, `.codex`, `.pi`, `.omp`, `.agents` — table in `products.py`);
method COPY / SYMLINK / CUSTOM. Load-bearing rules to keep in mind while
coding: never resolve an ambiguous dest silently, never hardcode a product
convention, REPO×SYMLINK must warn + gitignore, COPY must record
provenance, CUSTOM rewiring is pinned to `(collection, rev)` and fails
loudly when stale. Details, metadata design, and use cases: `docs/SPEC.md`.

## coding

### `ihate_work.ai.meta_skills`

The real manager: an interactive click-based CLI that installs a skill, or a
collection of skills, into a new or existing dest. Module map:

- `model.py` — the vocabulary: `SourceKind` (OWN/EXTERNAL), `DestKind`
  (HOME/REPO/DIR), `Method` (COPY/SYMLINK/CUSTOM), and the `Skill`, `Dest`,
  `InstallPlan` dataclasses.
- `discover.py` — find skills (dirs containing `SKILL.md`) in `my/` and in
  each submodule; uninitialized submodules still show up as collections.
- `products.py` — the per-product skill dir table (marker, project skills
  dir, global skills dir); kept in sync with `docs/skill-dirs.md`.
- `dest.py` — classify a target path into per-product `Dest` candidates
  (root: HOME > REPO > DIR), raising `AmbiguousRoot` instead of walking up
  to a repo root silently.
- `install.py` — `plan()` validates a triple and collects the special-rule
  warnings; `execute()` performs COPY/SYMLINK/CUSTOM, records provenance,
  and maintains the manager-owned skills-dir `.gitignore` (symlinks +
  manifest transient; the dest repo's root .gitignore is never touched).
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
- `cli.py` — click commands: `list`, `install`, `status`, `uninstall`.
  `install`/`uninstall` with no positional args run the interactive wizard;
  with args they are fully scriptable.

Tests are colocated as `*_test.py` (vibra convention). Entry point is
`__main__.py`; run it via `./cli`, not by importing directly.

### `./cli`

The wrapper: ensures the venv exists (`make -s deps`), then execs
`venv/bin/python -m ihate_work.ai.meta_skills`. It preserves the caller's
cwd, so the manager can treat cwd as the default install dest.

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
<gh-username>/<repo>`, then commit `.gitmodules` + the pinned rev.
