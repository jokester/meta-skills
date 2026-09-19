---
name: code-plan
description: "Use when the user wants to plan a feature, refactor, or domain before coding — produces or updates docs/plan-{topic}.md with concrete, locally-testable tasks that code-impl and code-manager can execute."
allowed-tools: [Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion]
---

# code-plan — Produce an executable plan doc

Turn a goal or idea into `docs/plan-{topic}.md` — the single source of truth for the
work. The plan is an _interface_: `code-impl` executes one task per run in a fresh
context, `code-manager` walks whole milestones. Everything an implementor needs must
be in the plan doc or reachable from its References section.

## Steps

### 1. Survey before planning

Don't guess, read or ask. Read, in order: any prior idea/design doc for this
topic (per the repo's doc taxonomy), the code the work will touch, the repo's
rulebook (via CLAUDE.md's pointer — and from its index the topic rules the work
touches), the target subproject's `Makefile` (how tests run). If the repo has no
rulebook, ask the user for the conventions to record in the plan's Conventions &
constraints section. Note what exists vs what the user assumes exists.

### 2. Grill until concrete

Interrogate the user until every task is scoped, actionable, and **locally
testable** — verifiable by `make test`-style checks with no dependency on a running
service, secret, or remote API (same bar as spawn-worktree's step 0). A task that
can't be locally verified must be redesigned, or explicitly marked
`(human-verified)` with the manual check spelled out.

Don't bake guesses into tasks — park them under Open questions instead.

### 3. Write the plan doc

```markdown
# Plan: {title}

## Goal

{What done looks like. Include explicit non-goals.}

## References

- {idea/design doc — why relevant}
- {entry-point files, kb docs, external links}

## Conventions & constraints

{Plan-level notes code-impl must follow: target subproject, naming, perf/compat
constraints. Omit anything the repo's rules docs already say.}

## Milestone 1 — {name}

- [ ] {task} — acceptance: {the test/check that proves it}
- [ ] …

## Open questions

{Unresolved decisions. A task blocked on one of these says so.}

## Decision log

- {YYYY-MM-DD}: {decision + one-line why}
```

### 4. Review the plan before finishing

- Tasks are MECE, dependency-ordered, and each is **one worktree, one merge** in
  size — it must fit a single code-impl session.
- Every task has an acceptance check.
- Nothing in the plan contradicts what the survey found in the code.

## Rules

- Plans rot. When later work finds reality diverged, amend the plan and append to
  the Decision log — never force an invalidated task through.
- Update an existing plan in place; don't fork `plan-{topic}-v2.md`.
