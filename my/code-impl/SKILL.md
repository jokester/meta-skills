---
name: code-impl
description: "Use when implementing a task from a plan doc (docs/plan-*.md) — validates the plan against current code with fresh eyes, implements one task with tests in an isolated worktree, commits, and hands off to code-merge."
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, Skill]
---

# code-impl — Implement One Plan Task

Pick up one task from a `docs/plan-{topic}.md`, implement it with tests in an
isolated worktree, and commit. This skill does **not** merge — `code-merge` reviews
and merges. It is designed to run in a fresh context (e.g. a subagent spawned by
`code-manager`): assume nothing from prior sessions.

## Steps

### 1. Load the plan and conventions

- Read the plan doc (user- or manager-specified; otherwise the most recently
  modified `docs/plan-*.md`).
- Read the repo's rulebook (via CLAUDE.md's pointer — the name varies per repo)
  and, from its index, the topic docs the task touches (typically the language
  rules, which include the testing rules). If the repo has no rulebook, stop and
  ask rather than implementing against guessed conventions. Then the plan's
  "Conventions & constraints" section.
- Read the target subproject's `Makefile` (tests, deps, format targets).

### 2. Validate the plan with fresh eyes

Plans rot between planning and implementation. Before writing anything, verify the
task's assumptions against the code **as it exists now**: the files, APIs, and
behaviors the task names. Read all existing code the task will touch or depend on.

If the task is invalidated (target moved, approach obsoleted, acceptance check
impossible): **stop**. Report what diverged and propose a plan amendment (Decision
log entry) — do not implement a stale task, and do not silently reinterpret it.

### 3. Pick the task

The specified task, or the first unchecked `- [ ]` in the plan. One task per
invocation.

### 4. Isolate in a worktree

Follow `spawn-worktree` steps 1–2 (setup + develop) — it is the mechanism, this
skill is the policy. Skip creation only when this session was already placed in a
dedicated worktree (e.g. by code-manager); then just verify with
`git worktree list` that you're not on the main checkout.

### 5. Implement

- **Readable, testable, minimal.** Only what the task asks for. No drive-by
  refactors, speculative features, or over-abstraction.
- **Match existing patterns.** New code should look like the neighboring code.
- **Stable APIs.** Exported functions get a short docstring and stable signature.
- **Comments are for "why".** Code carries "what" and "how".

### 6. Write tests

Every behavior change ships with tests, following the repo's language rules for
test naming and placement; test behavior, not implementation. The task's
**acceptance check** from the plan must be among them.

### 7. Verify in the worktree

`make -C LOCATION-SUFFIX test` (and lint/typecheck/format targets where present).
All green before the task counts. Fix code or tests — never skip or delete a
failing test.

### 8. Flip the checkbox — inside the worktree

Change the task's `- [ ]` to `- [x]` in the plan doc **in the worktree** and include
it in the commit. The checkbox then lands on the main branch atomically with the
code when code-merge fast-forwards — a rejected merge leaves the plan on main
untouched. Do not modify other tasks.

### 9. Commit and report

Commit on the temp branch (`git -C LOCATION-SUFFIX commit`). Then report:

- Which task was completed, and the worktree/branch paths for code-merge
- Files created/changed
- Design decisions made (and why)
- Anything noticed that affects upcoming tasks or the plan

## Rules

- Never merge back — that is code-merge's job, with its own fresh-eyes review.
- Do not change code outside the current task's scope.
- If a task is ambiguous or blocked on an Open question in the plan, stop and ask
  rather than guessing.
