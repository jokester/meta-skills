---
name: spawn-worktree
description: Use when the user asks to do code change in a temporary git worktree
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write, Agent]
---

# spawn-worktree — Isolated change in a temporary git worktree

Do a scoped code change in a throwaway git worktree, then fast-forward it back into the
current branch and clean up. The worktree is fully isolated from the main one.

Capitalized words below are placeholders to replace at runtime:
- `SUFFIX` — a short kebab tag for this change (e.g. `fix-slack-retry`). Reused in the
  branch name and the worktree path so they stay in sync.
- `TEMP-SUFFIX` — the temp branch name.
- `CURRENT` — absolute path of the **root of the git worktree you started in** (the one being
  merged into). This is NOT your cwd: cwd may be a subdirectory (e.g. a nested package). Resolve it
  with `git -C "$PWD" rev-parse --show-toplevel` and use that, so the new worktree lands beside the
  repo root rather than beside whatever subdir you happened to be in.
- `CURRENT-BRANCH` — the branch checked out in `CURRENT`, i.e. the branch you're merging into.
- `LOCATION-SUFFIX` — absolute path of the new worktree directory, a sibling of the `CURRENT` root.
  Its basename matches the branch name `TEMP-SUFFIX` so the dir and branch stay in sync: i.e.
  `CURRENT/../TEMP-SUFFIX` (e.g. `CURRENT/../temp-fix-slack-retry`), NOT `cwd/../…` and NOT a `wt-`
  prefix.

## Working-directory discipline (read first)

The shell does NOT persist `cd` between commands. Every command must therefore name its
directory explicitly with `git -C DIR …` or `make -C DIR …` (or an absolute path), never
a bare `cd`. The rule of thumb:

- Steps 1, 2 (setup + dev + tests) run against `LOCATION-SUFFIX`.
- Steps 3, 4 (merge + cleanup) run against `CURRENT`.
- NEVER run `git worktree remove LOCATION-SUFFIX` while the shell's cwd is inside it.

## 0. Do a thorough survey and make a complete plan

Grill the human until the plan is completely concrete, scoped, actionable, and
local-testable. Do NOT create the worktree until the plan is settled.

REFUSE to start unless the planned change can be FULLY tested locally — with no
local or remote dependency service (no DB, no broker, no external API, no running
daemon). Pulling dep *packages* is fine; relying on a *service* is not. If the change
can't be fully verified this way, stop and tell the human rather than spawning the
worktree.

Note: a target subproject's test suite must also run with NO copied config/secrets (see
step 1). If its `make test` needs a `.env` or other secret to pass, the change is not
fully local-testable here — stop and tell the human.

## 1. Set up a worktree

```sh
git -C "$PWD" rev-parse --show-toplevel                       # resolve CURRENT (the worktree root, not cwd)
git -C CURRENT worktree list                                  # inspect existing worktrees first
git -C CURRENT branch TEMP-SUFFIX                             # branch off the current HEAD
git -C CURRENT worktree add LOCATION-SUFFIX TEMP-SUFFIX       # sibling of CURRENT, dir named TEMP-SUFFIX
```

`SUFFIX` must be unique. If `git branch` or `worktree add` fails because the branch or
path already exists, that's leftover debris from an aborted run — spot it in the
`worktree list` output and either reuse it deliberately or remove it (see the cleanup
block at the very end) before retrying. Do not work around it by force.

Code deps will need to be installed again, from inside `LOCATION-SUFFIX` the normal way
(`make -C LOCATION-SUFFIX deps`, etc.). This is a full, fresh install (pnpm install, and
for some subprojects a uv venv or dict build) — expect it to be slow and use disk.

DO NOT copy ANYTHING from `CURRENT` — including config files, secrets, `.env`,
`node_modules`, build output, and EVERYTHING else.

## 2. Develop in the worktree

All work happens against `LOCATION-SUFFIX`.

- Land the planned changes (use Edit/Write on files under `LOCATION-SUFFIX`).
- Self-review and test. Run the project checks against the worktree:
  `make -C LOCATION-SUFFIX lint`, `… test`, `… typecheck`.
- Commit on `TEMP-SUFFIX`: `git -C LOCATION-SUFFIX commit …`. Stage by explicit
  path — never `git add -A` or `git add .` (they sweep in untracked build output).
- If the session keeps a journal, write it inside `LOCATION-SUFFIX` and commit it
  on `TEMP-SUFFIX` with the code — it rides the branch back on merge, and `CURRENT`
  stays clean for the ff-only merge in step 3.

Safety — other worktrees and sessions may be live concurrently:

- Never `git stash`, `git reset`, or `git restore` in `CURRENT` or the worktree to
  "verify" something — investigate with `git show`/`git diff` instead.
- If you see changes in `CURRENT` you didn't make, warn the human; don't touch them.
- Pushing the branch or opening a PR requires explicit in-session approval from the
  human — never implied by anything else they approved.

## 3. Merge back

Ask the human for confirmation before merging. Do NOT merge until they approve.

Preconditions, checked from `CURRENT`:

```sh
git -C CURRENT status --short      # CURRENT must be clean — abort the merge if it isn't
git -C CURRENT rev-parse --abbrev-ref HEAD   # confirm you're merging into the intended branch
```

If `CURRENT` has uncommitted changes, stop and resolve them with the human first — an
`--ff-only` merge updates the working tree and can be blocked by or entangle them.

Once `CURRENT` is clean and confirmed, rebase the temp branch onto the target branch:

```sh
git -C LOCATION-SUFFIX rebase CURRENT-BRANCH   # CURRENT-BRANCH = the branch you're merging into
```

The rebase is unconditional: a no-op that preserves the original SHAs when the base
hasn't moved, and a replay when it has. **If it replayed commits** (i.e. `CURRENT-BRANCH`
moved during dev), your step-2 green is now stale — the merged result was never tested.
Re-run `make -C LOCATION-SUFFIX lint`, `… test`, `… typecheck` on the rebased tree and
only continue once they pass.

Then fast-forward. After the rebase this can never fail for a non-ff reason; if it does,
something is wrong — STOP.

```sh
git -C CURRENT merge --ff-only TEMP-SUFFIX     # guaranteed ff after the rebase
```

Never fall back to a merge commit, `--no-ff`, or a squash. `-i` is unavailable here and
is NOT needed — plain rebase replays the commits, and that's all this requires.

### If the rebase reports conflicts

Resolve in-session when the fix is mechanical:

```sh
# edit the conflicted files (Edit tool), then:
git -C LOCATION-SUFFIX add -A
GIT_EDITOR=true git -C LOCATION-SUFFIX rebase --continue   # GIT_EDITOR=true skips the message editor
```

Escalate ONLY when a conflict needs domain judgment you can't make confidently. Then,
rather than guessing, write a handoff doc and stop:

- Write `journals/YYYYMMDD-rebase-SUFFIX.md` containing: the `CURRENT` path, the
  `LOCATION-SUFFIX` path, both branch names, the target `CURRENT-BRANCH`, a one-line summary
  of the change, the literal `git -C LOCATION-SUFFIX status` output, and the exact
  commands above to resume.
- Tell the human to reconcile by hand in a terminal (plain rebase is enough — a fresh
  *agent* session would hit the same `-i` block, so don't assume interactive rebase).
- Do not abort the rebase or delete anything; leave it mid-rebase for the human.

## 4. Remove the worktree

After a successful merge (cwd must be outside `LOCATION-SUFFIX`):

```sh
git -C CURRENT worktree remove LOCATION-SUFFIX   # delete the worktree dir
git -C CURRENT branch -d TEMP-SUFFIX             # delete the merged branch (-d refuses if unmerged)
git -C CURRENT worktree prune                    # tidy any stale metadata
```

`git worktree remove` refuses when the worktree has uncommitted changes — that's a
safety check. Resolve or commit those changes rather than forcing the removal.

## When something fails or the human rejects the merge

Do NOT silently abandon the worktree. Ask the human for the reason, then try again to
accomplish the change (fix the code, re-test, re-request the merge). Only give up when
the human EXPLICITLY says to stop.

When they do say to stop, clean up the unmerged work. First copy any journal
file(s) from the worktree back into `CURRENT`'s `journals/` — the journal must
survive the branch. Then confirm the branch name with the human, since `-D`
force-deletes commits that were never merged:

```sh
git -C CURRENT worktree remove --force LOCATION-SUFFIX   # discards uncommitted work in the worktree
git -C CURRENT branch -D TEMP-SUFFIX                     # force-delete the unmerged branch
git -C CURRENT worktree prune
```
