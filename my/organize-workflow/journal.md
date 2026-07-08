# organize-workflow journal

Append one entry per run, newest last. Never delete entries — rejected proposals are recorded so they aren't re-proposed.

Entry template:

```markdown
## YYYY-MM-DD

- **Window:** <last run date> → <this date>; examined: <projects / transcripts / repos / materials>
- **Decisions:** <what was created/merged/promoted, one line of rationale each>
- **Rejected:** <proposals turned down, and why>
- **Open questions:** <carry to next run>
```

---

## 2026-07-09

- **Window:** genesis run (done ad hoc in a shoushu session, before this skill existed)
- **Decisions:**
  - shoushu: merged `process-inbox` + `import-text` + `import-doc` + `import-paypay-card` into one `/import` skill (router + on-demand detail files). Evidence: text args were routed between skills by improvisation.
  - shoushu: promoted "guess first, ask only when unsure" to CLAUDE.md and the skill — user: "most of the time agent's guess is good".
  - shoushu: promoted "balance assertions are factual checkpoints; reconcile gaps via `Expenses:Unknown` `\"balance\"` transactions" — user explanation + pattern in `book/2025-10.bean`, `book/2025-11.bean`.
  - Created this skill as a repeatable routine (user: learn from facts/opinions, build order, create reusable tasks — not task-specific).
- **Rejected:** none
- **Open questions:**
  - Run cadence — time-based (e.g. monthly via schedule/cron) or on-demand when friction is felt?
  - Should other repos' CLAUDE.md get the guess-first rule too, or is it shoushu-specific?
