---
name: organize-workflow
description: Repeatable meta-routine — learn how the user actually works from facts (any records the user has or points at — logs, histories, chats, documents, data) and opinions (targeted grilling), build order out of what's learned, and turn recurring work into reusable tasks (skills, scripts, checklists, routines). Keeps a journal between runs; run it periodically, not per-task.
argument-hint: [optional focus — a workflow, a project, or materials to digest | empty for a full periodic run]
---

A recurring practice, not a task-specific tool. Each run: **learn** what happened since the last run, **build order** (organize knowledge into rules and structure), and **create reusable tasks** so the next occurrence of the same work is cheaper. State persists in `journal.md` in this skill dir — every run starts by reading it and ends by appending to it.

## Step 0. Open the journal

Read `journal.md` (recreate it if missing — entry format is documented at its top and in Step 5). It gives you: the last run's date (= start of this run's evidence window), decisions already made (don't relitigate), and **open questions** carried forward (ask them this run if evidence or opportunity allows).

## Step 1. Collect facts

Facts are records of what actually happened — in what order, how often, and what it cost (round-trips, corrections, redo). They can come from **anything**:

- materials the user hands over or points at: notes, TODO lists, chat exports, emails, tickets/issues, calendars, spreadsheets, ledgers, browser history, photos of paper
- histories that accumulate on their own: git logs of active repos, shell history, Claude Code session transcripts, app/server logs
- anything else — if it records behavior over time, it's minable

Start each run by asking (or deciding from the focus): *which sources cover this window and focus?* Then mine them. `mining.md` in this skill dir is the recipe cookbook — a generic procedure for unfamiliar sources plus concrete commands per known source family. **When you mine a new kind of source, append a recipe to `mining.md`** so the next run starts warmer.

Signals to hunt, whatever the source (record each with a source pointer):

| Signal | Reads as |
|---|---|
| Same kind of work appearing ≥3 times | reusable-task candidate |
| A question always answered the same way | promote the answer to a default |
| Corrections / redos ("no", "actually", done twice) | anti-pattern → rule with the why |
| An improvised deviation that was kept | codify it |
| A documented step consistently skipped | delete or rewrite the step |
| Approval round-trips that always end in "yes" | remove the approval |
| Same context re-explained in different places | write it down once, in the right place |
| Multi-step sequence done by hand each time | script it or make it a task |

## Step 2. Collect opinions (grilling)

Facts say what happens; opinions say what *should*. Grill with AskUserQuestion, batched, every question anchored to evidence and proposing a default:

> "All five times this came up you chose the same option — make it the standing default and stop being asked?"

Also ask the carried-forward open questions from the journal. When evidence is thin (new area, no records), run the standing interview instead: What did you do repeatedly lately? Where was your time wasted? What do you always answer the same way? What order/priority do you want that keeps coming out wrong? Never ask what a record already answers.

## Step 3. Build order

Reconcile facts + opinions into structure:

- **Inventory** existing guidance wherever it lives — CLAUDE.md files, `.claude/skills/`, this collection, project docs, scripts, checklists. Find overlap, contradiction, dead references, and rules the facts show being violated.
- **Decide placement** for each learning at the smallest scope that covers all its occurrences: a rule in one project's docs < a project skill/script < a cross-project skill in this collection < a journal note (real but not yet actionable).
- **Propose** as one table before changing anything — one approval round for the batch, not per item:

| Proposal | Kind | Evidence |
|---|---|---|
| Merge overlapping task docs into one with a router | merge | same steps duplicated in three places; users jumped between them |
| Promote a constant answer to a written default | rule promotion | asked N times, answered identically each time |

Kinds: **new reusable task** (skill, script, checklist, template), **rule promotion**, **merge**, **split**, **delete/rewrite step**, **doc fix**, **new routine** (recurring job — time-triggered → cron/schedule; user-triggered → skill).

## Step 4. Create reusable tasks

Implement approved proposals. A reusable task takes whatever form fits the trigger and the user's tools: a Claude skill, a shell script, a checklist in a doc, a template file, a scheduled job. For Claude skills, read `authoring.md` in this skill dir for conventions (progressive disclosure, guess-first defaults, evidence-cited rules, after-write hygiene); for other artifacts, place them next to what they organize and reference them from there.

- Project-specific → that project's repo (`.claude/skills/`, docs, or scripts dir); update its CLAUDE.md or index; grep for names made stale.
- Cross-project → this collection (`meta-skills/my/`); skills get symlinked into `~/.claude/skills/`.
- Commit in every repo that changed, message style matching its history.

## Step 5. Close the run

Append a journal entry: date, evidence window, sources examined, decisions made (one-line rationale each), proposals rejected (and why — so they aren't re-proposed), open questions for next run. Report to the user; if any Claude skills were created or renamed, remind that they load next session. Suggest the next run when the journal shows the cadence (default: after a few weeks of activity).
