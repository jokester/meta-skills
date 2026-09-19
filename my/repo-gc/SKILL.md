---
name: repo-gc
description: "Detect silent rot in a repo's meta layer: CLAUDE.md map vs reality, dead path references in skills and docs, incomplete indexes, workspace hygiene. Run periodically or when docs feel stale. Reports drift; only fixes with user approval."
allowed-tools: [Read, Glob, Grep, Bash]
---

# repo-gc — Detect silent rot in the meta layer

Code fails loudly; the meta layer — CLAUDE.md, skills, docs, indexes — rots silently: claims outlive the reality they describe. This skill mechanically checks the claims. **Report findings; do not fix without user approval** (except trivially safe ones the user asks for).

Adapt each check to what the repo actually has; skip checks with no subject.

## Checks

### 1. CLAUDE.md map vs reality

- Every subproject/directory CLAUDE.md names exists on disk, and every top-level dir that looks like a subproject appears in CLAUDE.md.
- If the repo tags subprojects with a status (active/incubating/dormant), compare tags with git activity: `git log -1 --format=%ad --date=short -- <dir>`. Tagged active but untouched for months — or dormant but recently busy — is drift.
- Docs meant to stay thin pointers (README, CLAUDE.md): flag if they regrew content their targets already carry.

### 2. Referenced paths exist

For each `.claude/skills/*/SKILL.md` and each doc, extract path-like references and check they exist on disk. Red flags regardless of existence:

- **Absolute checkout paths** (`/home/...`, `/Users/...`, `~/...`) inside a skill or doc — worktrees move; paths must be repo-root-relative. (Deliberate cross-repo pointers are the exception, and should say so.)
- References to renamed files — grep the old basename across the repo to suggest the successor.

### 3. Index completeness

For each index the repo maintains (e.g. `journals/index.md`, any `index-*.md`, a memory index), compare its entries against the files in its scope (`comm` on sorted lists): every in-scope file indexed, no entry pointing at a missing file, no obviously stale hooks.

### 4. Workspace hygiene

- Committed build artifacts: `git ls-files | grep -E '/(dist|out|build)/'`
- Leftover template/scaffold names in manifests.
- Anything the repo's own rulebook makes mechanically checkable (version/catalog drift, naming rules) — read the rulebook and run what is cheap to check.

## Report format

Group findings by check, one line each: `<file>: <claim> — <reality>`. End with a short prioritized fix list. If everything is clean, say so in one line.
