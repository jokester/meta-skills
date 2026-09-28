---
name: workflow
description: "The session workflow, start to merge: revise the specs with the human (BACKLOG → TODO, new or changed features), plan the doc and code tasks into the journal, study the code each touches, do the tasks with fresh subagents in one worktree, then check, review and ff-merge. Use when a session is asked to change what the system does; a TODO never reaches the mainline."
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, Agent, Skill, AskUserQuestion]
---

# workflow — one session, one branch, five phases

The spec is the task ledger (`spec-writing` skill). On the mainline a section is a built feature or
a `BACKLOG:`; **`TODO:` exists only on a branch** and reads "what this branch will make true". A
session is one worktree and one branch; its spec diff is its plan, its journal is its trail, and
nothing merges while a TODO remains. This skill dispatches; it writes specs with the human and
spawns subagents for code — fresh context per task is the point: the implementor reads the spec
without planning-session bias, and the reviewer reads the diff without implementor bias.

## 1. Revise — with the human

- Survey before drafting — don't guess, read or ask: the owning spec, the repo's glossary if it
  keeps one, the rulebook (via CLAUDE.md's pointer) and the package or layer rules the work
  touches, the target subproject's `Makefile`. No rulebook? Ask for the conventions to follow.
  Read your position: `BACKLOG:` items the requested work makes nearly free, or that share files
  with it, and open questions the work would close.
- Set up the worktree: `spawn-worktree` steps 1–2 (the mechanism). Everything below happens in it.
- Draft the TODO sections in the worktree's specs — a BACKLOG promoted with its designed body, a new
  feature, or a built feature to change (`TODO:` on the heading, the body rewritten to the target).
  New nouns go to the glossary first. Show the drafts and grill until each is concrete; **the human
  decides every marker**. Suggest the positional items in one line each with the evidence; without
  a yes they stay out of scope.
- Rules and terms that change with the work are edited now, too: the doc diff is the plan.
- Run `review` on the doc diff before moving on.

## 2. Plan tasks — into the journal

Open this session's journal (`journal` skill, save mode) on the branch with the intent and the task
list: one task per TODO section, plus the doc-only tasks. Each task names its files, its acceptance
check — proven by the repo's check target, no service, secret or remote API — and, for a new file
or anything crossing two packages, its interface line: module, exports, imports. Order by
dependency; each task fits one `code-impl` run; note which pairs are file-disjoint. A task that
can't be verified locally is redesigned or marked `(human-verified)` with the manual check spelled
out. Open questions become `BACKLOG:` sections, not guesses baked into tasks.

## 3. Study

Validate each TODO against the code as it exists: read every file a task touches, its package's
public surface, the topic rules it engages. Amend the TODO wording in place when the code says
otherwise, with the human when the behavior itself moves. An external repo as reference →
`study-adapt`.

## 4. Do — fresh subagents in the same worktree

For each task, in the planned order:

1. Spawn a fresh subagent (Agent tool) told to follow `.claude/skills/code-impl/SKILL.md` for
   exactly this spec section in this worktree: pass the worktree path, the spec path, the heading
   verbatim, the journal's task line, and nothing else about prior context.
2. Parallel subagents only for tasks the plan marked file-disjoint and the human asked for.
3. A subagent that reports the task invalidated stops the loop: the human amends (back to phase 1
   for that section); never reinterpret and continue.
4. A subagent that fails twice from scratch stops the loop: the task is wrong-sized or
   under-specified — say so.
5. Relay a subagent's promotion and position suggestions verbatim; never act on them.

Between tasks, re-read the spec from the worktree — the marker just dropped — and tick the task in
the journal. Report `task N done — M remaining`.

## 5. Check, review, merge

- The check target green in the worktree, and no `TODO:` left in any spec: a leftover is an
  unfinished task, a section to demote to `BACKLOG:` (its design kept in the body), or a stopped
  session — never something to merge.
- Close the journal: decisions and their rejected alternatives, quirks, changes, open threads.
- `spawn-worktree` steps 3–4: one `review` of the whole branch diff in a fresh context, the merge
  gate (ask, unless pre-authorized at the start of the run), rebase, retest, ff-only, clean up. A
  rejected review gets a fix round in the same worktree — a fresh subagent scoped to the findings —
  at most two; then escalate with the findings and the worktree path.
- Summarize: sections landed (with SHAs), tasks blocked and why, amendments proposed.

## Rules

- Ask two gating questions once, at the start: approve each merge or auto-merge on a clean review
  (auto-merge skips only the ask; a must-fix finding still blocks); and the stop condition — the
  named sections, or every TODO the human marks this session.
- Sequential by default; spawn-worktree's safety rules bind the whole run.
- This skill edits specs, terms, rules and the journal. Code is the subagents'.
