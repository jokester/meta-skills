---
name: code-deps
description: "Manage Python/TypeScript dependencies in this monorepo. Use this to install/update deps in the smooth way."
allowed-tools: [Read, Edit, Bash, Glob, Grep]
---

# code-deps — Dependency Management

Add, remove, upgrade, and troubleshoot packages across the vibra monorepo. The
authoritative reference (layouts, cooldown policy, catalogs, frozen packages,
troubleshooting) is `docs/rules-deps.md` — read it first. All commands run from the
repo root of whichever worktree you're in; never hardcode an absolute checkout path.

## Critical Rules

- **NEVER run `pip install` or `uv pip install` directly.** Edit the requirements
  file, then `make -C py deps` (or `make -C py deps-{domain}` for per-domain deps).
- **NEVER run `npm install`.** This repo uses pnpm exclusively.
- **NEVER edit `venv/` contents manually.** The venv is managed by uv via the Makefile.
- The supply-chain cooldown (uv `exclude-newer`, pnpm `minimumReleaseAge`) is
  policy — do not bypass it to get a fresher version.

## Python

1. **Add**: edit `py/requirements.txt` (grouped under a comment header, no version
   pin) — or `py/requirements-{domain}.txt` for heavy/domain-specific packages —
   then `make -C py deps` / `make -C py deps-{domain}`.
2. **Remove**: delete the line, `make -C py deps`. Clean state needs a venv
   recreate (see rules-deps.md).
3. **Upgrade**: `make -C py upgrade-deps` (pur, respects cooldown + `FREEZE_PY_REQ`),
   then `make -C py deps`.

## JS/TS

1. **Add**: `cd <package> && pnpm add [-D] <name>`. If the dep is (or should be)
   shared across packages, use the catalogs in `pnpm-workspace.yaml` and reference
   it as `catalog:...` — see rules-deps.md.
2. **Upgrade**: `taze` for interactive checks, `pnpm update <name>` for one package.

## Troubleshooting

Work through the Troubleshooting section of `docs/rules-deps.md` (sentinel files,
pipdeptree, workspace-root `pnpm install`) before improvising.
