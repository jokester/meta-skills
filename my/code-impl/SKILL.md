---
name: code-impl
description: "The brief for one do-phase task: implement one `TODO:` section of a spec doc in the session's worktree — validate it against the code with fresh eyes, build it with tests, drop the marker, commit, report. Spawned by the workflow skill; never merges, never picks its own task."
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
---

# code-impl — Implement One Spec Task

Build exactly the `TODO:` section you were given, in the worktree you were given, with tests, and
commit with the marker dropped. This skill runs in a fresh context spawned by `workflow` phase 4:
assume nothing from prior sessions, and read what follows in order.

## 1. Load the task and the rules

- **The task**: the spec path, the heading verbatim, the worktree path `LOCATION-SUFFIX`, and the
  journal's task line (files, acceptance check, interface line) — all handed to you. Missing, or a
  `BACKLOG:` section named? Stop and ask. Never choose a task yourself.
- **The spec**, whole, and the repo's shared glossary for its words, if it keeps one.
- **The rules**: the repo's rulebook (via CLAUDE.md's pointer — the name varies per repo), then
  from its index the topic rules the task touches (language and testing rules, package or layer
  rules, config, deps). No rulebook? Stop and ask rather than implementing against guessed
  conventions.
- Read the target subproject's `Makefile` (check, test, deps, format targets).
- Confirm with `git -C LOCATION-SUFFIX worktree list` that the worktree is not the main checkout.
  Every command names it: `git -C`, `make -C`, absolute paths.

## 2. Validate with fresh eyes

The TODO was written before the code was read this closely. Verify its assumptions against the code
**as it exists now**: the modules, exports and behaviors it names or implies. Read every file the
task will touch or depend on.

If the task is invalidated (target moved, approach obsoleted, acceptance impossible) or its behavior
is not fully decided: **stop**. Report what diverged and propose the wording — do not build a stale
task, and do not silently reinterpret it.

**Read your position.** A neighbouring `BACKLOG:` section that this change makes nearly free, or
that touches the same files, earns a one-line suggestion with evidence in your report. Suggest
only; the task stays exactly the named section.

## 3. Design before code

Interface first: for a new file or anything crossing two packages or modules, hold to the journal's
interface line — module, exports, imports — or report why it cannot hold. Stay within the repo's
layering and each package's stated purpose.

## 4. Implement

- **Readable, testable, minimal.** Only what the section asks for. No drive-by refactors,
  speculative features, or over-abstraction.
- **Match existing patterns.** New code should look like the neighboring code.
- **Exports are stable**, each with a short doc comment; comments carry only the *why*.
- **Instrument as you go**, to the repo's observability standard (its rules doc or skill, if it
  has one): each transition, refusal and failure the task adds is visible the way its neighbours'
  are.
- Dependencies change only through `code-deps`.

## 5. Write tests

Every behavior change ships with tests, following the repo's language rules for test naming and
placement; test behavior, not implementation. The task's acceptance check is among them, and a spec
claim a test can pin gets pinned.

## 6. Drop the marker, then check

In the spec, in the worktree, remove `TODO: ` from the section heading and make its body true of the
code as built — still within budget, still user-facing (`spec-writing`). Touch no other section.
Then the repo's check target (`make -C LOCATION-SUFFIX check`, or its lint/test/typecheck
equivalents) green before the task counts: fix code or tests — never skip, delete, or annotate a
failing check away.

## 7. Commit and report

Commit on the branch (`git -C LOCATION-SUFFIX commit`, staging by explicit path). Then report:

- The section completed and the commit SHA
- Files created/changed; design decisions made, and why
- Anything that affects the remaining tasks, the spec, or the rules — an open question for a
  package, a promotion suggestion, an interface line that had to change

## Rules

- Never merge, never touch `CURRENT`, never edit another spec section or the journal — `workflow`
  owns those.
- Do not change code outside the task's scope.
- Ambiguous, or blocked on an open question? Stop and ask rather than guessing.
