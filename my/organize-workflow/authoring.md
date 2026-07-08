# Authoring conventions for created artifacts

Conventions for the reusable tasks this routine produces. Derived from practice; revise them here when a run's evidence contradicts them.

## Claude skills

### Shape

- **Progressive disclosure.** `SKILL.md` stays under ~100 lines: a routing table (what input → which procedure) plus shared rules. Case-specific detail goes in sibling `.md` files the agent reads on demand. Everything always-loaded costs context in every session.
- **One skill per user-visible task.** Merge skills that share routing or rules (a merged skill with a router beats several skills with duplicated tables). Split when a file grows past ~500 lines *and* its parts load on different occasions.
- **Names**: short, verb-first, stable. Renames break user habit and stale references — grep for the old name and update every mention (CLAUDE.md, docs, other skills).

### Rules inside skills

- **Guess first; ask only when unsure.** Encode defaults explicitly ("default: X") and enumerate the exact situations where asking is allowed. A skill that says "ask if ambiguous" without examples trains the agent to over-ask.
- **Every rule cites evidence.** Point at a real artifact in its repo or quote the user's stated reason. Rules without a visible why rot and get argued with.
- **Encode the why for anti-pattern rules.** "Never do X" is stronger with "because Y" attached.
- **No confirmation round-trips** for inferences the skill's own tables already determine. Write, then report what was inferred; the user corrects after the fact if needed.
- **Placement: smallest scope that covers all occurrences.** One project → that repo's CLAUDE.md or `.claude/skills/`. Multiple projects → this collection (`meta-skills/my/`) plus a symlink: `ln -s /home/mono/Projects/meta-skills/my/<name> ~/.claude/skills/<name>`.

### Hygiene

- **After-write section** in every skill that edits files: how to verify (the project's check command, with expected-noise filters spelled out), how to commit (message style copied from that repo's `git log`), what to archive.
- **Frontmatter**: `name`, `description` (the description is the routing hint the agent sees in every session — say *when* to use it, not just what it is), `argument-hint`.
- **Skills load at session start** — after creating, merging, or renaming, tell the user the change takes effect next session.

## Other artifacts (scripts, checklists, templates, docs)

- Place next to what they organize; reference them from that project's index (CLAUDE.md, README, or the doc they support) so they're discoverable without remembering they exist.
- Scripts: idempotent where possible, `--help` or a top comment stating trigger and effect.
- Checklists: each item observable (done/not-done decidable), ordered by real execution order from the evidence.
- Same evidence rule as skills: a checklist step or script behavior that came from a specific observed failure should say so in a comment.

## Always

- **Commit every change** in whichever repo it lands, including this collection.
