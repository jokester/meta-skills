# Survey: skill directory conventions per product (as of 2026-09)

The *format* is stable: the Agent Skills spec (<https://agentskills.io>,
originated by Anthropic, now an open standard — repo
<https://github.com/agentskills/agentskills>) defines a skill as a dir with
`SKILL.md` (YAML frontmatter: `name`, `description`) plus optional
`scripts/`, `references/`, `assets/`. What differs per product is *where*
skills are discovered.

## the table (mirrored in `products.py`)

| product | user-level (HOME) | project-level | discovery depth |
|---|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` | one level (`<root>/<name>/SKILL.md`) |
| Codex CLI | `~/.codex/skills/` | `.codex/skills/` | one level |
| pi | `~/.pi/agent/skills/` | `.pi/skills/` | recursive |
| oh-my-pi (omp) | `~/.omp/agent/skills/` | `.omp/skills/` | one level per root |
| neutral `.agents` | `~/.agents/skills/` | `.agents/skills/` (also `.agent/`) | one level |

## per-product notes

- **Claude Code** also loads: enterprise managed-settings dir (highest
  precedence), nested `<subdir>/.claude/skills/` in monorepos,
  `--add-dir` dirs, and plugin `skills/` dirs. Precedence: enterprise >
  personal > project. Live-reloads SKILL.md changes.
- **Codex CLI** ships built-ins in `~/.codex/skills/.system` (don't touch).
  Skills load at startup only — a new session is needed after install.
  Invoked via `$` mention or auto-matched on description.
- **pi** (badlogic/pi-mono) discovers *recursively* under its roots — the
  only surveyed product that tolerates nested `<root>/group/<name>/`.
  Explicitly aims for compatibility with Claude Code / Codex skills.
- **omp** (can1357/oh-my-pi, pi fork) is a multi-convention reader: besides
  its native dirs it reads *project-level* `.claude/skills`,
  `.codex/skills`, `.pi/skills`, `.agent[s]/skills`, `.github/skills`, and
  opencode dirs by default (priority: native 100 > plugins 90 > claude 80 >
  claude-plugins/agents/codex 70 > opencode 55 > github 30 > managed 5).
  Foreign *user-level* dirs are opt-in (`enableClaudeUser` etc.).
- **`.agents/`** is the emerging product-neutral convention; omp treats it
  as near-native. Claude Code and Codex do NOT read it (yet), so it can't
  be the single install target.

## consequences for this manager

1. An install target is `(dest root, product)` — the product table lives in
   `products.py`; dest resolution derives markers and skills dirs from it,
   never hardcoding `.claude`.
2. Always install *flat*: `<skills root>/<skill-name>/`. One-level
   discovery is the least common denominator (only pi reads nested).
3. A project dest with only `.claude/skills` already serves omp too (it
   reads foreign project roots by default) — installing natively for omp is
   optional at project level, necessary at user level.
4. Not supported yet, candidates for later: `.github/skills/` (GitHub
   layout), opencode, per-product plugin/managed dirs (read-only territory —
   never install into `.system` or managed dirs).

Sources: [agentskills spec](https://github.com/agentskills/agentskills) ·
[Claude Code skills docs](https://code.claude.com/docs/en/skills) ·
[Codex skills docs](https://github.com/openai/codex/blob/main/docs/skills.md) ·
[Codex skills guide](https://developers.openai.com/codex/skills) ·
[pi skills docs](https://badlogic-pi-mono.mintlify.app/coding-agent/skills) ·
[pi-skills README](https://github.com/badlogic/pi-skills) ·
[omp skills docs](https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md)
