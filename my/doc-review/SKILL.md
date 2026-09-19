---
name: doc-review
description: "Review documents for correctness, freshness, simplicity, completeness, consistency, and adherence to project doc conventions. Checks multiple perspectives and flags issues with concrete suggestions."
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# doc-review — Multi-Perspective Document Review

Review the specified document(s) from multiple perspectives, flagging issues with
concrete suggestions. Documents are how work is shared across sessions, humans, and
agents — a wrong or bloated doc is worse than none.

## Steps

### 1. Determine what to review

- If the user specifies docs, use those.
- If nothing is specified, review docs touched by the current uncommitted changes
  (`git diff HEAD --name-only -- '*.md'`).
- Read each doc fully, and skim what it links to — a doc can only be judged against
  its neighbors.

### 2. Load the conventions

- `docs/rules-doc.md` — the authoritative doc conventions (taxonomy, indexes,
  writing style, journal locations).
- `CLAUDE.md` — the subproject map and the Superset exception.
- Any index in scope (`journals/index.md`, `docs/index-text.md`,
  `deps/superset/doc/index-superset.md`) — indexed docs must have accurate lines.

### 3. Review from each perspective

Skip any perspective with nothing to flag.

- **Correctness & freshness** — Do named files, paths, commands, and versions still
  exist and behave as stated? Verify with Glob/Bash, don't trust the prose. Stale
  claims are must-fix: a reader can't tell them from true ones.
- **Writing style** — apply `rules-doc.md` "Writing style" as loaded in step 2: the
  where/what/why-vs-how formula, its three litmus tests (staleness, duplication,
  one-glance), and MECE/focus. Flag each failing sentence with which test it fails.
- **Completeness** — Are there gaps a reader will hit (missing prerequisite, an
  undocumented step between two documented ones)? Distinguish goals from means:
  flag places where the doc prescribes a means without stating the goal, since
  those instructions can't be adapted when circumstances change.
- **Assumptions** — Flag statements that were assumptions at writing time but read
  as facts (e.g. about external tools' behavior, other repos, future plans). They
  should be marked as such or verified.
- **Consistency & conventions** — Naming matches the taxonomy; the doc is indexed
  where its peers are; terminology agrees with related docs.
- **Security** — No secrets, tokens, or internal URLs that don't belong in git.

### 4. Report findings

Grouped by document. For each finding:

1. **Location** — `docs/foo.md:42` (or section name)
2. **Perspective** — which lens caught it
3. **Issue** — one line
4. **Suggestion** — the concrete fix; for wording issues, propose the replacement text

Use the severity levels from the checklist in `docs/rules-dev.md` (must-fix / should-fix / nit).

### 5. Summary

- Total findings by severity
- Overall assessment (accurate / needs updates / misleading)
- If a doc is good, say so — don't invent issues.

## Rules

- Verify factual claims against the repo before flagging or passing them.
- Do not flag style preferences the conventions don't cover; three real findings
  beat twenty nitpicks.
- Stale-path and wrong-fact findings outrank all wording findings.
