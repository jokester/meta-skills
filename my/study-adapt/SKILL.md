---
name: study-adapt
description: Study an external repo for conventions and designs worth learning, bank the findings as a docs/study-*.md verified reading log, adopt what earns it (spec-first), and follow up later by diffing the repo since the study's pinned commit. Use when asked to study, learn from, compare against, or follow up on another codebase.
---

# study-adapt

## Ground rules

- Studied repos are independently studied references: name them freely, cite them precisely,
  never frame one as this project's origin or prior form.
- Study-class discipline: non-normative; pin repo + commit + date; every claim carries a
  `file:line` citation (line numbers drift — treat as starting points); record negative results
  ("grep for X returned nothing"); end with an **Open items** tail. The repo's doc taxonomy (via
  CLAUDE.md's pointer) may add to this.
- Facts over assumptions: verify claims against the source; mark what was not verified.

## Modes

Pick by input:

- **study** — repo path(s)/URL(s) not yet covered by a `docs/study-*.md`.
- **follow-up** — a repo an existing study already pins.
- **no input** — list `docs/study-*.md` with pinned commit vs the repo's current HEAD; propose
  follow-ups on stale pins; ask which to run.

## Study

1. Read this repo's contracts first — CLAUDE.md, the rulebook, the package or layer rules, the
   overview or glossary — so findings are judged as **deltas against our practice**, not
   absolutes.
2. Explore the target (parallel read-only agents for large repos). Each explorer gets the
   calibration context and must return, per finding: WHAT the convention is, WHERE (paths), and
   a one-line novelty judgement relative to our practice.
3. Bank `docs/study-<repo>.md` (or extend one that covers the topic): pinned commit + date;
   what is novel vs our practice; a **ranked steal list** (value-to-effort); explicit
   **do-not-copy** items with reasons; Open items, each trigger-gated where adoption should wait
   ("when CI lands", "when the CLI package lands").
4. Cross-check: a finding that contradicts an existing rule or spec here is the most valuable
   kind — surface the clash explicitly rather than smoothing it over.

## Adapt

Only with the user's go-ahead, and spec-first:

1. Each adoption edits the **owning** rules doc or spec — the study stays non-normative. Mark
   the finding ADOPTED in the study, linking where the rule now lives.
2. Candidates that wait keep their trigger in the study's Open items.
3. Journal the round: what was adopted, what was deliberately not, and why.

## Follow-up

1. Read the study doc; note the pinned commit. Fetch the repo if it has a remote.
2. Diff `pin..HEAD`, focused on: files the study cites, areas of its Open items, and mechanisms
   we ADOPTED — did upstream evolve, harden, or abandon them?
3. Update the study in place: new pin, corrected observations (it describes the present of the
   studied repo), Open items resolved or extended.
4. If an adopted rule's upstream basis was abandoned or reworked, surface that prominently —
   whether to follow is the user's call, not the skill's.

## Deliverable

Lead the chat summary with the verdict (what is worth adopting / what changed since the pin),
then the banked or updated study doc, then — adapt mode only — the rule/spec edits and the
journal entry. Commit per repo convention.
