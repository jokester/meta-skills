---
name: review
description: "Review a diff — code and docs together — for correctness, readability, testability, security, spec-first, doc class purity and the repo's rules docs. Flags issues with concrete fixes. Run before committing, and once per branch before merging."
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# review — one pass over code and docs

A spec-first diff touches code and its spec together, and the gate that matters most needs both
sides. Review the whole diff against the repo's rules; flag only actionable findings with a concrete
fix. If you wrote the code under review, run this in a fresh context (Agent tool) and act on what it
returns.

## 1. Determine what to review

- The user's files or diff range; else the uncommitted changes (`git diff HEAD`, plus
  `git diff --cached`); on a branch, `git diff CURRENT-BRANCH...TEMP-SUFFIX`.
- Read every changed file in full, and skim what a doc links to — a doc can only be judged against
  its neighbours. Never review what you haven't read.

## 2. Load the rules

Read CLAUDE.md and follow its pointers to the rulebook (the name varies per repo): its review
checklist and coding principles for code; its doc conventions — taxonomy, where knowledge lives,
index locations, severity levels — for docs. From the rulebook's index, the topic rules the diff
touches (language, packages or layers, config, deps), and any topic skill the repo carries for them
(observability, spec writing — `spec-writing` for a spec doc). A violation of a rules doc is
must-fix, not a nit. If the repo has no rulebook, stop and ask which bar to review against.

## 3. The cross-cutting gates

- **Spec first** — a change that adds or alters user- or operator-visible behavior includes the
  owning spec; a new noun is in the glossary, if the repo keeps one; a new export fits its
  package's stated purpose. Missing spec: must-fix.
- **No TODO reaches the mainline** — a branch diff about to merge leaves no `TODO:` in any spec
  (`git grep -n 'TODO:' -- <spec glob>`); each dropped marker's body is true of the code as built,
  and the drop touches only its own section. Leftover TODO: must-fix.
- **Acceptance** — for a spec task, the diff does what the section says and the journal's
  acceptance check is among the tests.

## 4. Code perspectives

The checklist: **correctness**, **readability**, **tests**, **security**. Plus:

- **Boundaries and surface** — imports respect the repo's layering; a package's public surface
  exports what callers intend; heavy deps stay where the rules put them.
- **Comments** — each survivor is a *why* the code cannot show; a "why" that is really a contract
  belongs in the spec.
- **Escape hatches** — every type cast, non-null assertion, ignored result or lint suppression
  states why the ignored case is impossible.
- **Observability** — per the repo's standard: each transition, refusal and failure the change adds
  is visible, errors keep their stack, no secret or user content in a signal.

## 5. Doc perspectives

- **Correctness & freshness** — named files, paths, sections, commands, versions exist and behave as
  stated; verify with Glob/Grep, don't trust the prose. Stale claims are must-fix: a reader can't
  tell them from true ones.
- **Class purity** — each doc stays in its class per the repo's taxonomy: a spec says what the user
  or operator gets, never how or why; a rules doc constrains and points into code, never restates
  it; a study is non-normative and pins repo, commit and date. Prose false if the code changed
  alone is "how": cut it, link the file.
- **Spec shape** — per `spec-writing`: one surface, within budget, a marker only on a heading, on
  the mainline only built features and `BACKLOG:`, no DONE.
- **Present tense** — live docs describe the present; the trail and superseded designs belong in
  `journals/`.
- **Litmus tests** — staleness (will this sentence rot?), duplication (already said elsewhere?
  link), one glance (does it land without re-reading?).
- **Completeness & assumptions** — gaps a reader will hit; means prescribed without the goal;
  assumptions reading as facts.
- **Indexes** — a new doc is indexed where its peers are; terminology agrees with the glossary.
- **Paths & security** — no absolute checkout path; no secrets, tokens, internal URLs.

## 6. Report

Grouped by file: `path:line`, the perspective, a one-line issue, the concrete fix — replacement text
for wording, code when helpful. Severity per the repo (typically must-fix / should-fix / nit).
Totals by severity and a verdict: ship it / needs changes / needs rethink. Clean is a short report;
don't invent issues.

## Rules

- Verify before flagging or passing; stale-path and wrong-fact findings outrank wording.
- Three real findings beat twenty nitpicks; don't flag style the rules don't cover.
- **Ratchet** — an issue seen before in this repo becomes a mechanism — a lint rule, a conventions
  test reading the tree or the manifests (never a doc as input), or a rules line — instead of a
  third review comment.
