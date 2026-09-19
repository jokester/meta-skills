---
name: repo-gc
description: "Garden the repo's meta layer: verify CLAUDE.md's subproject map matches reality, indexes are complete, and paths referenced in skills/docs still exist. Run periodically or when docs feel stale. Reports drift; only fixes with user approval."
allowed-tools: [Read, Glob, Grep, Bash]
---

# repo-gc — Detect silent rot in the repo's meta layer

This is an experimental-garden repo: domains go dormant naturally, and that's fine.
What rots silently is the *claims about them* — CLAUDE.md sections, skill paths,
indexes. This skill mechanically checks those claims. **Report findings; do not fix
without user approval** (except trivially safe ones the user asks for).

## Checks

### 1. CLAUDE.md map vs reality

- Every top-level directory that looks like a subproject appears in CLAUDE.md, and
  every subproject CLAUDE.md lists exists on disk.
- Status tags vs git activity: for each subproject run
  `git log -1 --format=%ad --date=short -- <dir>`. A dir tagged **active** but
  untouched for >2 months, or tagged **dormant** but recently busy, is drift.
- README.md should stay a pointer — flag if it regrew a project list.

### 2. Referenced paths exist

For each `.claude/skills/*/SKILL.md` and each `docs/*.md`, extract path-like
references (`deps/...`, `py/...`, `docs/...`, `journals/...`, `_shared/...`) and
check they exist. Two extra red flags regardless of existence:

- **Absolute checkout paths** (`/home/...`, `/media/...`, `~/vibra/...`) inside a
  skill or doc — worktrees move; paths must be repo-root-relative. (Exception:
  deliberate cross-repo paths like `~/thecoo/fbp-ax/` in superset-twin-sync.)
- References to files that were renamed (grep the old basename across the repo to
  suggest the successor).

### 3. Index completeness

Each index must cover exactly the files in its scope (compare with `comm`):

- `journals/index.md` ↔ `journals/*.md`
- `deps/superset/doc/index-superset.md` ↔ `deps/superset/journals/*.md`
- `docs/index-text.md` — newest listed journal should not lag far behind the newest
  text/NLP journal in `journals/index.md`'s Text group.

### 4. Workspace hygiene

- Committed build artifacts: `git ls-files | grep -E '/(dist|out)/'`
- Leftover template names: `grep '"name".*-template' */package.json`
- Catalog drift: workspace packages hardcoding versions for deps that exist in
  `pnpm-workspace.yaml` catalogs (skip incubating/dormant subprojects per CLAUDE.md).

## Report format

Group findings by check, one line each: `<file>: <claim> — <reality>`. End with a
short prioritized fix list. Skip checks with nothing to flag. If everything is
clean, say so in one line.
