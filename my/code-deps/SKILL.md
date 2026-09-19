---
name: code-deps
description: "Add, remove, or upgrade dependencies the repo's sanctioned way — via its manifests and Makefile targets, never raw package-manager installs. Use whenever dependencies change."
allowed-tools: [Read, Edit, Bash, Glob, Grep]
---

# code-deps — Dependency changes, the repo's way

Every repo routes dependency changes through its own machinery (manifests, lockfiles, Makefile targets, supply-chain policy). This skill's job is to find and follow that machinery — never to improvise with raw installer commands.

## Steps

1. **Find the repo's dep workflow.** Read CLAUDE.md and follow its pointer to the dependency rules doc (the name varies per repo). Also read the target subproject's `Makefile` for `deps`/`upgrade` targets. If neither documents a workflow, stop and ask the user rather than improvising.
2. **Edit the manifest, run the target.** Change the declared requirement (requirements file, `package.json`, workspace catalog, …), then run the repo's install target (`make -C <dir> deps` or equivalent). Lockfiles and venvs are outputs, never the thing you edit.
3. **Verify.** Run the repo's test/lint targets on whatever the change touches.

## Rules

- **Never run raw installer commands** (`pip install`, `uv pip install`, `npm install`, …) — they bypass the manifest and produce state the next `deps` run silently reverts. Which package managers are sanctioned at all is the repo's call; the rules doc says.
- **Never hand-edit managed dirs** (`venv/`, `node_modules/`) or lockfiles.
- **Respect supply-chain policy.** If the repo pins a release cooldown (e.g. uv `exclude-newer`, pnpm `minimumReleaseAge`), that is policy — do not bypass it to get a fresher version.
- **Shared deps go in the shared place.** If the repo has workspace catalogs or shared requirement groups, check the rules doc before adding a per-package copy.
- Troubleshoot via the repo's dep rules doc before improvising fixes.
