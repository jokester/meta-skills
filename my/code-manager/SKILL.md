---
name: code-manager
description: "Use when the user wants a plan executed end-to-end — orchestrates code-plan / code-impl / code-merge across fresh-context subagents, one task per worktree, until the milestone is done or blocked."
allowed-tools: [Read, Glob, Grep, Bash, Agent, Skill, AskUserQuestion]
---

# code-manager — Run the plan → impl → merge loop

Dispatcher, not implementor: this skill never writes code itself. It reads the plan,
spawns fresh-context subagents for each phase, relays results, and stops when done
or blocked. Fresh context per phase is the point — the implementor reads the plan
without planning-session bias, and the reviewer reads the diff without implementor
bias.

## Steps

### 0. Setup — once per run

- Locate the plan doc (`docs/plan-*.md`). If none exists for this work, run
  `code-plan` first (in-session, with the user — planning is interactive).
- Ask the user two gating questions up front:
  1. **Merge gating** — approve each merge individually, or auto-merge on a clean
     review? (Auto-merge only skips step 4 of code-merge; a must-fix finding still
     blocks.)
  2. **Stop condition** — one task, one milestone, or the whole plan?

### 1. Per-task loop

For each unchecked task within the stop condition, sequentially:

1. **Implement.** Spawn a fresh subagent (Agent tool) instructed to follow
   `.claude/skills/code-impl/SKILL.md` for exactly this task of this plan doc. Pass
   the plan path and task text verbatim; pass nothing else about prior context.
2. **Review + merge.** On impl success, spawn a _different_ fresh subagent
   instructed to follow `.claude/skills/code-merge/SKILL.md` for that worktree,
   telling it the user's merge-gating choice.
3. **Rejected review.** Feed the must-fix findings to a fresh fix subagent working
   in the same worktree (code-impl steps 5–9, scope = the findings). Max two fix
   rounds; then stop and escalate to the human with the findings and worktree path.
4. **Plan invalidated.** If the impl agent reports the task diverged from reality,
   stop the loop and surface its proposed amendment — the human (optionally with
   code-plan) amends; don't amend the plan unilaterally and continue.

### 2. Between tasks

Re-read the plan doc from the main checkout — the merge just changed it (checkbox
flip, possibly Decision-log entries). Report one-line progress to the user:
`task N merged (SHA) — M remaining`.

### 3. End of run

- Summarize: tasks merged (with SHAs), tasks blocked and why, plan amendments
  proposed.
- Run `/journal-save` — the run is a session worth journaling.

## Rules

- Sequential by default. Parallel worktrees only when tasks are provably
  independent (no shared files) AND the user asked for parallelism.
- All spawn-worktree safety rules bind the whole run: never stash, never mutate a
  dirty CURRENT, ff-only merges.
- If the same task fails impl twice from scratch, stop — the plan task is probably
  wrong-sized or under-specified; say so.
