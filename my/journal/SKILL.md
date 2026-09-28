---
name: journal
description: "The session journals under journals/: open this session's entry at the start with its intent and task plan, append as decisions land, close it before the merge — and search past entries to answer what was done, discovered, changed, or left open. Given a question it searches; otherwise it saves."
argument-hint: [a question about past sessions → search | empty or "save" → open, append to, or close this session's entry]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
---

# journal — save this session, search past ones

Journals are the one place the past lives: how decisions were reached, what was tried, what
surprised. Specs and rules say what is true now; a journal says how it got that way. It is also the
session's working document: opened in `workflow` phase 2 with the task plan, appended as the
session goes, closed before the merge. Mode by input: a question → **Search**; nothing, or "save" →
**Save**.

CLAUDE.md may carve out per-subproject journal locations with their own indexes — honor them in
both modes.

## The format

- **File**: `journals/YYYYMMDD-p{N}-{topic}.md`. `N` is a repo-wide sequence — the highest `p`
  number present plus one (`ls journals | grep -o 'p[0-9]*' | sort -V | tail -1`). One session,
  one number; a session spanning days keeps its number and appends dated sections.
- **Topic slug**: kebab-case, naming each distinct thread the session touched
  (`authelia-bootstrap-nested-services`, not `refactor`) — it is how the entry is found. Longer
  multi-thread slugs beat one generalized label. Never `unknown`.
- **Frontmatter**: `date: YYYY-MM-DD` and `tldr:` (one to three sentences — the outcome and the
  decisions that produced it). Title `# p{N} — {brief title}`.
- **Body**: `## Plan` first when the session runs the workflow — one line per task: the spec
  section, its files, its acceptance check, its interface line when it has one; ticked as tasks
  land. Then one `##` per thread — the question, what was found, what was decided and why, what it
  cost; `file:line` where it helps; an `## Open threads` tail when something is unfinished.
- **Index**: `journals/index.md`, one entry per journal grouped by theme, superseded entries
  flagged _historical:_ rather than deleted:

  ```markdown
  - [FILENAME.md](FILENAME.md) —
    {one or two lines: the searchable essence — the decisions, not the activity}
  ```

  Many journals but no index yet? Suggest creating one.

## Save

1. **Placement.** In a temporary worktree (spawn-worktree / code-impl): write to the worktree's own
   `journals/` and commit on the temp branch — it rides the branch back on merge, and the main
   checkout stays clean for the ff-only merge; an abandoned branch's journal is copied back before
   deletion. Otherwise: `journals/` at the repo root.
2. **Open** (start of a session): a new file per § The format with `date`, a provisional `tldr`,
   the intent, and `## Plan` when there is one. In a worktree, commit it on the branch; it is the
   plan of record and rides the merge.
3. **Append** (as the session goes): tick plan lines, add a thread when a decision lands or
   something surprises; a session spanning days adds dated sections. Never rewrite history.
4. **Close** (before the merge, or at the end of a session), from the conversation only — no extra
   exploration: each **decision** with the alternative rejected and the reason (the core of the
   entry); discoveries and quirks; experiments that failed and why; the files changed and the
   substance of each; open threads; the final `tldr`. Concise but specific, for a future reader
   skimming; *why* and *what surprised* over play-by-play; omit a section with nothing useful.
5. **Index.** Add or refresh the entry under the best-fitting group, or open a new heading.
6. **Promote** (§ Promote).

## Search

1. **Read the question**: what/when, why, a gotcha, an open thread, which files — and the time
   window if it names one.
2. **Index first**: skim the relevant groups of `journals/index.md`; it often names the files
   outright.
3. **Then grep** across `journals/*.md` for the question's keywords, synonyms in parallel
   (`git grep -li`). Nothing? Scan `grep "^tldr:" journals/*.md`. Time-based? `ls -t journals/*.md`
   and read the newest.
4. **Read** frontmatter and title of each hit to judge relevance, then the relevant files in full.
5. **Answer** directly, citing `journals/FILENAME.md` and the section. Chronological when it spans
   sessions; quote a discovery verbatim when it is the answer; flag contradictions, the later entry
   usually being right; check whether a later journal resolved an open thread. If the journals do
   not cover it, say so — never fill the gap from memory.

## Promote

A fact that is durable — about the system, a rule, a tool, or an external repo, not this session's
circumstance — does not belong only in a journal. Per the repo's doc taxonomy: behavior → the
owning spec; a constraint → the owning rules doc; an observation about another repo → its study
doc; an open question about a package → wherever the repo tracks those. On save: do it now, or
record the promotion as an open thread. On search: when the answer was found only in a journal,
say where it should live.
