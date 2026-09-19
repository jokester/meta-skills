---
name: code-merge
description: "Use when a temp-worktree branch is ready to come back to the main branch — reviews the diff with fresh eyes (code-review checklist + plan acceptance criteria), then rebases, ff-only merges, and cleans up the worktree."
allowed-tools: [Read, Glob, Grep, Bash, Edit, Skill, Agent]
---

# code-merge — Review a worktree branch, then merge it

The gate between `code-impl` and the main branch. Review happens with fresh eyes —
ideally in a different context than the one that wrote the code — and nothing merges
with unresolved must-fix findings. The git mechanics are `spawn-worktree`'s; this
skill decides _whether_ they run.

## Steps

### 1. Locate the work

`git worktree list` from the main checkout. Identify `CURRENT` (target checkout),
`CURRENT-BRANCH`, the temp worktree `LOCATION-SUFFIX`, and its branch `TEMP-SUFFIX`
(spawn-worktree's placeholder names). Confirm the temp branch has commits ahead:
`git -C CURRENT log --oneline CURRENT-BRANCH..TEMP-SUFFIX`.

### 2. Review with fresh eyes

- Diff: `git -C CURRENT diff CURRENT-BRANCH...TEMP-SUFFIX`.
- Apply the review checklist from the repo's rulebook (via CLAUDE.md's pointer —
  the same one code-review uses), plus the topic rules docs relevant to the diff.
  If the repo has no rulebook, stop and ask which bar to review against.
- If the work came from a plan task, check the diff against that task's
  **acceptance criteria** in `docs/plan-*.md`, and verify the checkbox flip is
  included and touches only that task.
- Re-run the checks yourself — don't trust a reported green:
  `make -C LOCATION-SUFFIX test` (+ lint/typecheck where present).

### 3. Verdict

- **Must-fix findings or red tests** → do not merge. Report the findings and hand
  back to code-impl (or the human). The worktree stays; nothing is deleted.
- **Clean (nits at most)** → proceed.

### 4. Merge gate

Ask the human before merging — unless they pre-authorized merges for this run (e.g.
via code-manager's up-front gating question). Never treat a passed review as
implicit merge approval. Pushing the branch or opening a PR is a separate action
that always needs its own explicit in-session approval — local merge authorization
never implies it.

### 5. Merge and clean up

Execute `spawn-worktree` §3 (verify CURRENT clean → rebase TEMP-SUFFIX onto
CURRENT-BRANCH → **re-test if the rebase replayed commits** → `merge --ff-only`)
and §4 (worktree remove, branch -d, prune). Its conflict-escalation and
failure-handling rules apply verbatim.

### 6. Report

Merged SHA(s), review findings (including accepted nits), and any plan/task state
that changed.
