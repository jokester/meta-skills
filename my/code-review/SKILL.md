---
name: code-review
description: "Review changed code for correctness, readability, testability, security, and adherence to the repo's conventions. Flags issues with concrete suggestions."
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# code-review — Multi-Perspective Code Review

Review the specified code (files, diff, or staged changes) against the repo's own rulebook, flagging issues with concrete suggestions.

## Steps

### 1. Determine what to review

- If the user specifies files or a diff range, use that.
- Otherwise review the current uncommitted changes: `git diff HEAD` (plus `git diff --cached` for staged changes).
- Read every changed file in full. Do not review code you haven't read.

### 2. Load the repo's rules

Read CLAUDE.md and follow its pointer to the coding rulebook (the name varies per repo). From the rulebook's index, open the topic docs relevant to the diff (language rules, dependency rules, domain kb docs). These are authoritative — violations are must-fix, not nits. If the repo has no rulebook, stop and ask the user which bar to review against.

### 3. Review from each perspective

Evaluate every changed file against the rulebook's review checklist plus the topic rules from step 2. Only report actionable findings — skip a perspective with nothing to flag.

### 4. Report findings

Grouped by file. For each finding: `path/to/file.py:42`, the perspective that caught it, a one-line issue, and a concrete fix (show code when helpful). Use the repo's severity levels (typically must-fix / should-fix / nit).

End with totals by severity and a verdict (ship it / needs changes / needs rethink). If the code is clean, say so — don't invent issues.

## Rules

- Do not suggest changes you haven't verified against the actual code.
- Do not flag things already handled correctly; if the code is good, the review is short.
- **Ratchet:** an issue seen before in this repo should become a mechanism — propose a lint rule, conventions test, or rulebook line instead of writing the same review comment a third time.
