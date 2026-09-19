---
name: doc-review
description: "Review documents for correctness, freshness, simplicity, completeness, and consistency with the repo's doc conventions. Flags issues with concrete suggestions."
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# doc-review — Multi-Perspective Document Review

Documents are how work is shared across sessions, humans, and agents — a wrong or bloated doc is worse than none. Review the specified doc(s) and flag issues with concrete fixes.

## Steps

### 1. Determine what to review

- If the user specifies docs, use those.
- Otherwise review docs touched by the current uncommitted changes (`git diff HEAD --name-only -- '*.md'`).
- Read each doc fully, and skim what it links to — a doc can only be judged against its neighbors.

### 2. Load the repo's conventions

Read CLAUDE.md and follow its pointers to the doc conventions (the name varies per repo). Note the taxonomy, index locations, and severity levels it defines. If the repo defines no doc conventions, stop and ask the user which bar to review against.

### 3. Review from each perspective

Skip any perspective with nothing to flag.

- **Correctness & freshness** — Do named files, paths, commands, and versions still exist and behave as stated? Verify with Glob/Bash, don't trust the prose. Stale claims are must-fix: a reader can't tell them from true ones.
- **Writing style** — Apply the repo's style rules plus the generic litmus tests: **staleness** (will this sentence rot?), **duplication** (is this already said elsewhere?), **one-glance** (does it land without re-reading?). Docs carry where/what/why; code carries how.
- **Completeness** — Gaps a reader will hit (missing prerequisite, an undocumented step between two documented ones). Flag means prescribed without the goal stated — those instructions can't be adapted when circumstances change.
- **Assumptions** — Statements that were assumptions at writing time but read as facts (about external tools, other repos, future plans). They should be marked as such or verified.
- **Consistency** — Naming matches the repo's taxonomy; the doc is indexed where its peers are; terminology agrees with related docs.
- **Security** — No secrets, tokens, or internal URLs that don't belong in git.

### 4. Report

Grouped by document. For each finding: location (`docs/foo.md:42` or section), perspective, one-line issue, and the concrete fix — for wording issues, propose the replacement text. Use the repo's severity levels (typically must-fix / should-fix / nit).

End with totals by severity and an overall verdict (accurate / needs updates / misleading). If a doc is good, say so — don't invent issues.

## Rules

- Verify factual claims against the repo before flagging or passing them.
- Stale-path and wrong-fact findings outrank all wording findings.
- Three real findings beat twenty nitpicks; don't flag style the conventions don't cover.
