---
name: journal-save
description: "Use at the end of a work session (or when the user asks to journal) — creates or updates journals/YYYYMMDD-p{PID}-{topic}.md documenting the session's intent, investigations, quirks, experiments, and actual changes, and adds it to journals/index.md."
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# journal-save — Document This Session's Work

Create or update a journal entry capturing what happened in this conversation — the intent, investigations, discoveries, quirks, experiments, and actual changes made.

## Steps

### 0. Placement — the journal must survive the worktree

- **In a temporary/spawned git worktree** (e.g. one created by `/spawn-worktree`):
  write the journal to the worktree's own `journals/` and **commit it on the temp
  branch** — it rides the branch back on merge, and the main checkout stays clean
  for the ff-only merge. If the branch is later abandoned, the journal must be
  copied back to the main worktree before deletion (spawn-worktree's cleanup rules
  cover this).
- **In a normal checkout**: the plain `journals/` path at the repo root.
- CLAUDE.md may carve out per-subproject journal locations with their own indexes —
  honor them.

### 1. Determine the journal filename

The filename format is: `journals/YYYYMMDD-p{PID}-{topic}.md`

- Get the Claude Code PID via `echo $PPID` (stable across all bash calls in a session)
- Infer a kebab-case topic slug from the session's work. The slug is how this journal gets found later, so it must be **specific and findable** — name each distinct thread the session touched, not a single generalized label. Length isn't capped; longer multi-word slugs are encouraged when the session spans multiple threads.
  - Single-thread examples: `o11y-pipeline`, `quickwit-indexes`, `bgm-search` — verb-object pattern works well here.
  - Multi-thread example: `authelia-bootstrap-nested-services-standardization` — one session that stood up authelia, built a bootstrap-script convention, AND restructured to a nested-services layout. Each thread is a keyword the user might search on later.
  - Avoid generalized single-label slugs (e.g. `authelia-bootstrap-standard`) when the session also touched orthogonal topics — they won't surface for the other threads.
  - The topic should always be inferable from the conversation — never use `unknown`.

Examples:

- single-thread: `journals/20260324-p3593122-o11y-pipeline.md`
- multi-thread: `journals/20260506-p250437-authelia-bootstrap-nested-services-standardization.md`

### 2. Find or create the journal file

One PID may have multiple journals (the user can `/clear` and start a new topic within the same Claude Code process). Search for all journals with this PID:

```
journals/*-p${PPID}-*.md
```

If matches exist:

1. Read the first ~10 lines of each match (frontmatter + title) to understand its topic
2. If the current session's work fits an existing file's topic, update that file (append a new dated section — don't rewrite history)
3. If the current work is a clearly different topic from all existing files, create a new file

If no matches exist, create a new file.

### 3. Gather context

Run `echo $HOST $USER` to find hostname and username to populate the frontmatter with. Then collect the following from the conversation history — do NOT run extra exploratory commands:

- **Intent**: What did the user ask for? What was the goal?
- **Investigations**: What did we read, search, or explore to understand the problem?
- **Discoveries / Quirks**: Anything surprising, non-obvious, or worth remembering (gotchas, undocumented behavior, edge cases).
- **Experiments**: Anything we tried that didn't work, and why.
- **Changes**: What files were actually created, modified, or deleted? Summarize the substance of each change.
- **Open threads**: Anything unfinished, deferred, or worth revisiting.

### 4. Write the journal entry

Use this template:

```markdown
---
date: { YYYY-MM-DD HH:MM }
branch: { current git branch }
host: { hostname }
user: { username }
tldr: { One-sentence summary of the session's outcome }
---

# Journal: {brief title}

## Intent

{What the user wanted to accomplish.}

## What happened

{Narrative of the work — investigations, key decisions, pivots. Keep it concise but useful to future-you skimming old entries. Use subsections if the session covered multiple distinct topics.}

## Discoveries / Quirks

{Bullet list of non-obvious things learned. Omit this section if nothing surprising came up.}

## Changes

{Bullet list of files changed and what was done to each. Group by topic if the session touched multiple areas.}

## Open threads

{Anything left unfinished or worth revisiting. Omit if everything is wrapped up.}
```

### 5. Update the index

`journals/index.md` is the catalog — one line per journal, grouped by theme. If
the repo keeps one, add a line under the best-fitting group (create a new group
heading if none fits):

```markdown
- [FILENAME.md](FILENAME.md) — {short hook, ~10 words: the searchable essence}
```

When updating an existing journal whose scope grew, refresh its index line too. If
the repo has accumulated many journals but no index yet, suggest creating one.
(If CLAUDE.md routes this journal to a per-subproject location, update that
location's index instead.)

**Promote durable discoveries.** If a Discovery/Quirk is a lasting fact about a
tool or convention (not just this session's circumstance), it belongs in the
repo's knowledge docs (per its doc taxonomy — e.g. a `kb-*.md` or study doc) — add
it there now, or record the promotion as an Open thread. Journals are the log;
knowledge docs are where future sessions actually look.

### 6. Guidelines

- Be concise but specific. The journal is for the user to skim later, not a transcript.
- Focus on _why_ and _what was surprising_, not mechanical play-by-play.
- Use code references (`file:line`) where they help.
- If updating an existing entry, append a new dated section rather than rewriting history.
- Don't editorialize or add filler — if a section has nothing useful, omit it.
