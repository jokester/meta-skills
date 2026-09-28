---
name: spawn-worktree
description: "The worktree mechanism: set up a temporary git worktree and branch, develop and check in it, then bring the branch back — one fresh-context review of the whole diff, no TODO left in a spec, rebase, ff-only merge, clean up. Used by the workflow skill; use directly for a small change the human asks to do in a worktree."
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, Agent, Skill]
---

# spawn-worktree — Isolated change in a temporary git worktree

Do a scoped change in a throwaway worktree, review it, fast-forward it into the current branch, and
clean up. The worktree is fully isolated from the main one. This is the **mechanism**; the session's
phases are `workflow`'s and one task's brief is `code-impl`'s. Used directly, the change must still
be **locally testable** — the repo's check target proves it with no running service (DB, broker,
daemon), secret, `.env`, or remote API; pulling dep *packages* is fine — and its spec edit rides
the same branch (spec first). If it can't be verified that way, stop and tell the human before
creating anything.

Placeholders, replaced at runtime:

- `SUFFIX` — a short kebab tag for the change (`fix-slack-retry`), reused in branch and path.
- `TEMP-SUFFIX` — the temp branch name.
- `CURRENT` — absolute path of the **root of the worktree you started in**, the one being merged
  into: `git -C "$PWD" rev-parse --show-toplevel`. Not your cwd, which may be a package dir.
- `CURRENT-BRANCH` — the branch checked out in `CURRENT`.
- `LOCATION-SUFFIX` — absolute path of the new worktree, a sibling of `CURRENT` whose basename is
  the branch name: `CURRENT/../TEMP-SUFFIX` (e.g. `CURRENT/../temp-fix-slack-retry`).

**Entering with an existing worktree** (a `workflow` branch at phase 5, or a leftover): resolve
the placeholders from `git -C CURRENT worktree list`, confirm the branch is ahead
(`git -C CURRENT log --oneline CURRENT-BRANCH..TEMP-SUFFIX`), and start at step 3.

## Working-directory discipline

Name the directory on every command — `git -C DIR …`, `make -C DIR …`, absolute paths — never a
bare `cd`. Steps 1–2 run against `LOCATION-SUFFIX`; steps 3–4 against `CURRENT`. Never run
`git worktree remove LOCATION-SUFFIX` while the shell's cwd is inside it.

**Safety, binding throughout** — other worktrees and sessions may be live concurrently:

- Never `git stash`, `git reset`, `git restore`, or `git checkout --` in `CURRENT` or the worktree
  to "verify" something; investigate with `git show` / `git diff`.
- Changes in `CURRENT` you didn't make: warn the human, don't touch them.
- Stage by explicit path, never `git add -A` / `git add .`.
- Pushing the branch or opening a PR needs its own explicit in-session approval; nothing else the
  human approved implies it.

## 1. Set up the worktree

```sh
git -C "$PWD" rev-parse --show-toplevel                       # CURRENT
git -C CURRENT worktree list                                  # inspect existing worktrees first
git -C CURRENT branch TEMP-SUFFIX                             # branch off the current HEAD
git -C CURRENT worktree add LOCATION-SUFFIX TEMP-SUFFIX       # sibling of CURRENT
```

A branch or path that already exists is debris from an aborted run: reuse it deliberately or remove
it (step 5), never force past it. Install deps fresh inside the worktree
(`make -C LOCATION-SUFFIX deps` or the repo's equivalent; slow, uses disk). **Copy nothing from
`CURRENT`** — no config, secrets, `.env`, `node_modules`, venvs, build output.

## 2. Develop in the worktree

- Land the change under `LOCATION-SUFFIX`; self-review against the repo's rulebook.
- The repo's check target green (`make -C LOCATION-SUFFIX check`, or its lint/test/typecheck
  equivalents), and no `TODO:` left in any spec doc.
- Commit on `TEMP-SUFFIX`: `git -C LOCATION-SUFFIX commit …`.
- A session journal is written inside `LOCATION-SUFFIX` and committed on `TEMP-SUFFIX`; it rides
  the branch back, and `CURRENT` stays clean for the ff-only merge.

## 3. Review, then merge

Nothing merges unreviewed, and nothing merges with a must-fix finding.

**Review.** Diff `git -C CURRENT diff CURRENT-BRANCH...TEMP-SUFFIX` and apply the `review` skill
once over the whole branch: code and docs, the spec-first gate, the no-TODO gate, each dropped
marker's section true of the code, the journal's acceptance checks. **If you wrote the code, the
reviewer must not be you**: run it in a fresh context (Agent tool) and act on what it returns.
Re-run the check target yourself, and a grep for `TODO:` over the spec docs
(`git -C LOCATION-SUFFIX grep -n 'TODO:' -- <spec glob>`) must print nothing; a reported green is
not evidence.

**Verdict.** Must-fix findings, a red check, or a leftover TODO → don't merge; report and hand back
(a fix round in the same worktree; `workflow` caps these at two, and a TODO that will not land this
session is demoted to `BACKLOG:` with its design kept). The worktree stays. Clean, nits at most →
continue.

**Merge gate.** Ask the human before merging, unless they pre-authorized merges for this run
(`workflow`'s up-front question). A passed review is never implicit approval.

**Preconditions**, from `CURRENT`:

```sh
git -C CURRENT status --short                # must be clean — a dirty CURRENT blocks the merge
git -C CURRENT rev-parse --abbrev-ref HEAD   # confirm CURRENT-BRANCH
```

**Rebase, retest, fast-forward:**

```sh
git -C LOCATION-SUFFIX rebase CURRENT-BRANCH   # no-op if the base hasn't moved, a replay if it has
```

If it replayed commits, the step-2 green is stale: re-run the check target and continue only when
it passes. Then:

```sh
git -C CURRENT merge --ff-only TEMP-SUFFIX     # guaranteed ff after the rebase; if it fails, STOP
```

Never a merge commit, `--no-ff`, or a squash; `-i` is unavailable and not needed.

**Conflicts** during the rebase: resolve in-session when mechanical (`Edit`, then
`git -C LOCATION-SUFFIX add -A` and `GIT_EDITOR=true git -C LOCATION-SUFFIX rebase --continue`).
When a conflict needs domain judgment you can't make confidently, write a handoff
`journals/YYYYMMDD-p{N}-rebase-SUFFIX.md` (`N` per the `journal` skill) — both paths, both branch
names, a one-line summary, the literal `git -C LOCATION-SUFFIX status`, the commands to resume —
tell the human to reconcile in a terminal (plain rebase suffices; a fresh agent session would hit
the same `-i` block), and leave the rebase mid-way: abort nothing, delete nothing.

## 4. Remove the worktree

After a successful merge, cwd outside `LOCATION-SUFFIX`:

```sh
git -C CURRENT worktree remove LOCATION-SUFFIX   # refuses on uncommitted changes — resolve, don't force
git -C CURRENT branch -d TEMP-SUFFIX             # -d refuses if unmerged
git -C CURRENT worktree prune
```

Report: merged SHA(s), review findings including accepted nits, the spec sections that lost their
marker, the journal entry that rode along.

## 5. When the merge is rejected or something fails

Don't abandon the worktree silently. Ask the human for the reason and try again — fix, re-check,
re-request. Give up only when the human explicitly says stop. Then copy any journal from the
worktree into `CURRENT`'s `journals/`, confirm the branch name with the human (`-D` destroys
unmerged commits), and:

```sh
git -C CURRENT worktree remove --force LOCATION-SUFFIX
git -C CURRENT branch -D TEMP-SUFFIX
git -C CURRENT worktree prune
```
