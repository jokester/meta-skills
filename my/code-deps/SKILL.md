---
name: code-deps
description: "Add, remove, or upgrade dependencies the repo's sanctioned way — via its manifests, shared catalogs, release cooldown, pins and Makefile targets, never raw or --latest installs. Use whenever dependencies or toolchain versions change."
allowed-tools: [Read, Edit, Bash, Glob, Grep]
---

# code-deps — Dependency changes, the repo's way

The repo's dependency rules doc is the policy; this skill is the order of operations. Never
improvise with raw installer commands.

## Steps

1. **Read the policy.** Follow CLAUDE.md's pointer to the dependency rules doc (the name varies per
   repo) for the change at hand: the release cooldown, shared catalogs or requirement groups,
   capped or pinned packages, build-script allowlists, where CLI tools are declared. If the repo
   also rules where a heavy dependency may live (one package, one layer), read that too. No
   documented workflow at all? Stop and ask the user rather than improvising.
2. **Change the declaration where it lives.** A per-package dep: that package's manifest (via the
   package manager's own add command, run in that package); a dep shared by several packages: the
   shared catalog or group; a CLI tool: the repo's tool-version file. Upgrade with the sanctioned
   updater, never a `--latest`-style bypass of pins. Then run the repo's install target
   (`make -C <dir> deps` or equivalent). Lockfiles and managed dirs are outputs, never edited.
3. **Verify.** Run the repo's check target on whatever the change touches; for a new runtime dep in
   a layer with import or isolation guards, confirm those guards still pass.
4. **Record.** A dep that earns a rule (a pin, a cap, a carve-out) gets its line in the dependency
   rules doc — spec before code.

## Rules

- **Never run raw installer commands** (`pip install`, `uv pip install`, `npm install`, `npx -y`,
  a global install, …) — they bypass the manifest and produce state the next `deps` run silently
  reverts. Which package managers are sanctioned at all is the repo's call; the rules doc says.
- **Never hand-edit managed dirs** (`venv/`, `node_modules/`) or lockfiles.
- **Respect supply-chain policy.** A release cooldown (uv `exclude-newer`, pnpm
  `minimumReleaseAge`, …) is policy — never bypass it to get a fresher version.
- **Shared deps go in the shared place.** Check the rules doc before adding a per-package copy of
  something the catalog already carries.
- Troubleshoot via the rules doc before improvising a fix; a gotcha it lacks is a line to add
  there, not a workaround to remember.
