---
name: spec-writing
description: "How to write a spec doc (docs/spec-*.md by default): one surface per spec, what earns a section, the two-paragraph budget, the BACKLOG marker on the mainline and the branch-only TODO marker, how a task becomes or revises a feature, and where a new spec is indexed. Use when creating or editing any spec, or when deciding whether something belongs in a spec at all."
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

# spec-writing — the rules of spec documents

A spec is the **what** for users and operators — surfaces, behavior, setup, guarantees — readable
without opening the code, and normative: the system is wrong if it disagrees. How it differs from a
rules doc or a study: the repo's doc taxonomy (via CLAUDE.md's pointer). Specs live at
`docs/spec-{name}.md` unless the repo says otherwise; where the repo's own conventions conflict
with this skill, the repo wins.

## One surface per spec

`docs/spec-{name}.md` names one surface (`cli`, `web`, `session`, `slack`), usually the package
that owns it. The order of definition is spec → terms → public interface → code: a change that adds
or alters behavior edits the spec on the same branch, and a new noun lands in the repo's glossary
(if it keeps one) before a spec uses it. A new spec gets its line in the repo's spec index.

Skeleton:

```markdown
# spec-{name}

{One line: what the surface is.} Code package: `{path}`.

{Who runs or reaches it, with links to the neighbouring specs.} Config: {what of it is required}.

## {command, area, or feature group}

{≤2 short paragraphs: what the operator or user gets.}

### {feature}

{≤2 short paragraphs.}

### BACKLOG: {feature}

{≤2 short paragraphs: the gap or the question — or a parked design awaiting its session.}
```

## Features

A feature is behavior as the operator or user sees it, never how it works inside. Specs cover the
**major** features, never all of them: the code states every behavior; the spec adds the promise.
A section's body is at most **two short paragraphs**, each one or two sentences; related features
group under one heading and pool their budget (K features → 2K paragraphs). A table counts as one
paragraph. UI detail appears only when it is not trivial. A setup step, a command, a gotcha line
are fine; deep procedure is a Makefile target, a script or a study, and rationale sits at the code
or in a study, never in the spec.

## Markers: two states on the mainline, one on a branch

A marker is a heading prefix, on any heading level, and scopes **that section's own body** — a
sub-section carries its own state. A built child under a marked parent is a smell: split, or move
the marker.

- **No marker** — a built feature: the body is true of the code now.
- **`BACKLOG:`** — wanted, not scheduled: the gap or the open question, or a design parked for a
  later session. The only marker the mainline carries besides none.
- **`TODO:`** — **branch-only**: the body is what this branch will make true. It covers a BACKLOG
  promoted for the session, a new feature, and a **revision** — `TODO:` on a built feature with its
  body rewritten to the target. When the code matches, the marker is dropped in the same commit; a
  built feature is a plain section and DONE is never written.

**A TODO never reaches the mainline**: `spawn-worktree` refuses to merge while a grep for `TODO:`
over the specs prints anything, and a session that stops short demotes its TODO to BACKLOG, design
kept, rather than merging it. **The marker is the human's decision**: an agent drafts the body and
asks; it never sets or drops a marker unasked, except dropping the TODO of the section it was told
to build.

## Before saving

- Every sentence is about what the user or operator gets; nothing about internals, no rationale.
- No section over its budget; no past tense — the trail belongs to a journal.
- Every unbuilt feature is BACKLOG, or TODO on this branch only; every landed one has lost its
  marker. A gap tracked elsewhere too (an open question in a rules doc) links it rather than
  restating it.
- New nouns are in the glossary; a new spec is in the spec index.
- Run `review` before committing.
