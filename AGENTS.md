# meta-skills

This repo is my personal skill storage & manager: a monorepo that collects
agent skills (mine and other people's) and provides tooling to install them
into the places agents look for them.

## repo layout

- `my/` — my own skills, authored in this repo (OWN).
- `<author>-<repo>/` — external skill collections, vendored as git submodules
  (EXTERNAL). Naming convention: prefix with the upstream author, e.g.
  `obra-superpowers`, `mattp-skills`.
- `ja/` — language-specific group; same submodule rules, one level deeper
  (e.g. `ja/k16shikano-ja-tech-writing`).
- `src/ihate_work/meta_skills/` — the manager code (see "coding" below).
  `ihate_work` is a namespace package (no `__init__.py`), shared with my other
  repos.
- `cli`, `Makefile`, `requirements.txt`, `pyproject.toml` — tooling entry
  points (see "dev workflow" below).

## modelling of skills & installing

An install = (skill source, dest, method).

### the skills (source)

1. OWN: `/my` my own skills
2. EXTERNAL: external skills (git submodules, pinned to a revision)

### the install dest

1. HOME: the global skill dirs for agents (e.g. `~/.claude/skills`)
2. REPO: a git repo (identified by the `.git` entry at its root)
3. DIR: any dir containing special directories like `.claude` `.omp`

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

## coding

### `ihate_work.meta_skills`

The real manager: an interactive python script (click-based) that installs a
skill, or a collection of skills, into a new or existing dest.

Responsibilities:
- detect the dest kind (HOME / REPO / DIR) from the target path
- apply the special rules above (gitignore handling, warnings)
- for CUSTOM upstreams, hold the per-`(upstream_repo, upstream_rev)` rewiring
  steps

Entry point is `__main__.py`; run it via `./cli`, not by importing directly.

### `./cli`

The wrapper: ensures the venv exists (`make -s deps`), then execs
`venv/bin/python -m ihate_work.meta_skills`. It preserves the caller's cwd,
so the manager can treat cwd as the default install dest.

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
