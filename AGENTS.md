# meta-skills

This repo is my personal skill storage & manager: a monorepo that collects
agent skills (mine and other people's) and provides tooling to install them
into the places agents look for them.

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

## modelling of skills & installing

An install = (skill source, dest, method).

### the skills (source)

1. OWN: `/my` my own skills
2. EXTERNAL: external skills (git submodules, pinned to a revision)

### the install dest

A dest has two axes: the *root* (below) × the *product* (whose convention —
Claude Code `.claude`, Codex `.codex`, pi `.pi`, omp `.omp`, neutral
`.agents`). The per-product dir table lives in `products.py`; the survey
behind it is `docs/skill-dirs.md`. Nothing may hardcode `.claude`.

1. HOME: a product's global skill dir (e.g. `~/.claude/skills`,
   `~/.codex/skills`, `~/.pi/agent/skills`, `~/.omp/agent/skills`)
2. REPO: a git repo (identified by the `.git` entry at its root)
3. DIR: any dir containing a product config dir (`.claude`, `.codex`, ...)

Neither axis is ever decided silently: a path merely *inside* a repo, or a
root where zero/multiple product dirs exist, prompts the user (TTY) or
fails loudly (scripted; disambiguate with `--product` / the repo root).

### the installing (method)

1. COPY: the dest gets a permanent snapshot
2. SYMLINK: the dest gets a pointer back into this repo
3. CUSTOM: the upstream has its own install script
    - need to be studied case by case
    - often means the installed files are template-instantiated, so close to COPY
    - we may also rewire upstream to get what we want. These rewiring steps
      should be kept in our code, pinned to `(upstream_repo, upstream_rev)`
      matching the git submodules.

### special rules

1. (REPO & SYMLINK): the installed skills must be .gitignored in the dest
   repo (the manager should ensure this), and the user should be warned that
   this combination is only suitable when evaluating skills — collaborators
   won't have the symlink target.
2. COPY into a dest should record where the snapshot came from (skill name +
   upstream rev), so a later run can detect drift and offer to re-install.
3. Never install by hand-copying; always go through the manager so the rules
   above hold.

(TODO evaluate if we need more)

## install metadata (design decided, impl pending)

Why metadata at all: SYMLINK installs are self-describing (readlink points
back into this repo), but a COPY is indistinguishable from a hand-written
skill — without metadata there is no uninstall listing, no `status`, no
drift detection ("this copy came from obra/superpowers @ rev X, since
bumped"). Two stores with strictly split roles, both **never committed**:

1. **Per-dest manifest** — `.meta-skills.json` in the dest's skills dir
   (exists today). The single source of truth for "what is installed here":
   skill id, method, source rev, installed_at. It travels with the install
   and survives this repo being re-cloned or moved.
   - TODO: must be auto-gitignored in REPO dests (like symlinks already
     are); currently it would get committed.
2. **Dest index** — a local file in this clone (e.g. `var/dests.json`,
   gitignored). Stores *only the list of dest paths ever installed to* —
   deliberately no per-skill data, so the two stores cannot desync. Enables
   `status --all` (iterate known dests, read their manifests), bulk
   re-install after a submodule bump, and dangling-symlink cleanup. Stale
   paths get pruned on read; a lost index rebuilds itself as dests are
   touched again.

Known limitation (accepted): a COPY committed into a dest repo and cloned
on another machine has no provenance there — drift detection only works on
the machine that installed it. If that ever matters, the opt-in exception
is a small provenance file committed *inside* the copy (vendoring-note
style); skipped for now.

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
  warnings; `execute()` performs COPY/SYMLINK/CUSTOM, ensures gitignore for
  REPO & SYMLINK, and records provenance.
- `manifest.py` — `.meta-skills.json` next to installed skills: which skill,
  which method, which source rev — enables drift detection in `status`.
- `rewire.py` — registry of CUSTOM upstream adaptations, keyed by
  `(collection, upstream_rev)`; a bumped submodule makes the lookup fail
  loudly so the rewiring gets revisited.
- `gitutil.py` — thin git helpers (repo root, submodule revs, gitignore).
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
<author>-<repo>`, then commit `.gitmodules` + the pinned rev.
