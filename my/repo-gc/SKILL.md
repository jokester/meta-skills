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

For each `.claude/skills/*/SKILL.md`, each doc, CLAUDE.md, and the config files that cite docs in comments (`Makefile`, lint/test/tool configs, conventions tests), extract path-like references and doc names and check they exist on disk — a renamed doc leaves its old name in exactly these places. Red flags regardless of existence:

- **Absolute checkout paths** (`/home/...`, `/Users/...`, `~/...`) inside a skill or doc — worktrees move; paths must be repo-root-relative. (Deliberate cross-repo pointers are the exception, and should say so.)
- References to renamed files — grep the old basename across the repo to suggest the successor.

### 3. Index completeness

For each index the repo maintains (e.g. `journals/index.md`, the rulebook's index of topic rules, a spec index, any `index-*.md`, a memory index, a package registry against the package dirs), compare its entries against the files in its scope (`comm` on sorted lists): every in-scope file indexed, no entry pointing at a missing file, no obviously stale hooks.

### 4. Skills

- If `.claude/skills/.meta-skills.json` exists: every skill it lists has a directory, and every directory not listed there is a repo-native skill (named in `.claude/skills/README.md` when the repo keeps one). A listed entry with no directory is a fold or rename awaiting its backport to the collection.
- A skill that names a doc, a Makefile target, or a path names one that exists (check 2 covers the paths; check the targets against the Makefile).
- Vocabulary: a skill uses the repo's doc-class names only of docs of that class.

### 5. Workspace hygiene

- Committed build artifacts: `git ls-files | grep -E '/(dist|out|build)/'`
- Leftover template/scaffold names in manifests.
- Anything the repo's own rulebook makes mechanically checkable (version/catalog drift, naming rules, doc budgets, marker grammar) but no conventions test or lint covers yet — run what is cheap to check, and propose the guard (the Ratchet: a recurring finding becomes a mechanism).

## Report format

Group findings by check, one line each: `<file>: <claim> — <reality>`. End with a short prioritized fix list. If everything is clean, say so in one line.
