# meta-skills — product spec

What the skill manager must do, as observable behavior. Implementation
notes live in `AGENTS.md`; the per-product directory survey in
`skill-dirs.md`.

## goals & non-goals

Goals:

- One place to store skills I own and vendor skills others wrote.
- Install any of them into any place an agent product looks, safely:
  no silent guesses, no git pollution, provenance kept.
- Work the same interactively (TUI) and scripted (flags, CI-able).

Non-goals:

- Not a skill marketplace/registry client; sources are this repo only.
- Not a skill *authoring* tool; skills are edited directly.
- Never edits skill content on install (except CUSTOM rewiring, which is
  explicit and pinned).

## the model

An install = **(skill source, dest, method)**.

### skill

A directory containing `SKILL.md` (Agent Skills format,
<https://agentskills.io>). Skills always install *flat* —
`<skills root>/<skill-name>/` — because one-level discovery is the least
common denominator across products (see `skill-dirs.md`).

### source

1. **OWN** — skills authored in this repo, under `my/`.
2. **EXTERNAL** — skills vendored as git submodules, pinned to a revision,
   laid out as `<gh-username>/<repo>/`.

A *collection* is `my/` or one submodule. Uninitialized submodules still
appear as collections (with a hint to init), never silently vanish.

### dest = root × product

Two independent axes, and **neither is ever decided silently**.

The *root* — where structurally:

1. **HOME** — a product's global skill dir (`~/.claude/skills`,
   `~/.codex/skills`, `~/.pi/agent/skills`, `~/.omp/agent/skills`, ...).
2. **REPO** — a git repo, identified by `.git` at its root.
3. **DIR** — a plain dir carrying at least one product config dir.

The *product* — whose convention: Claude Code (`.claude`), Codex
(`.codex`), pi (`.pi`), omp (`.omp`), neutral (`.agents`). The table lives
in `skill-dirs.md`. Nothing in the product may hardcode one of them.

Resolution rules:

- A path that *is* a repo root, carries a product marker, or names a
  product's global dir (including parents like `~/.pi`) resolves cleanly.
- A path merely *inside* a repo is ambiguous (enclosing repo? this dir?):
  prompt in a TTY, fail loudly when scripted. Never walk up silently.
- Product choice: explicit flag wins; in a TTY, a multi-select with
  already-configured products pre-checked; scripted with exactly one
  configured product uses it, otherwise fails asking for the flag.
- One install may target several products at once (same root, several
  skills dirs).

### method

1. **COPY** — the dest gets a permanent snapshot (default for REPO dests:
   collaborators must get working content).
2. **SYMLINK** — the dest points back into this repo; content tracks this
   repo live (default for HOME/DIR dests: my machine, my clone).
3. **CUSTOM** — the upstream has its own install story (template
   instantiation etc.). Adaptations ("rewirings") are studied case by
   case and pinned to `(collection, upstream_rev)`; a bumped submodule
   must make the stale rewiring fail loudly, never run silently.

### special rules

1. **REPO × SYMLINK**: only suitable while *evaluating* a skill —
   collaborators won't have the symlink target. The user must be warned
   (once per install run, not once per skill), and the links must be
   transient in the dest repo by default: ignored via a `.gitignore` the
   manager owns *inside the skills dir* (which also ignores itself and the
   manifest). The dest repo's own root `.gitignore` — tracked, human-owned
   — is never edited.
2. **COPY records provenance** (skill id + source rev), so drift is
   detectable later and re-install can be offered.
3. All installs go through the manager — hand-copying bypasses the rules
   above and is out of contract.

(TODO evaluate if we need more)

## install metadata

Why: SYMLINK installs are self-describing (readlink points back here), but
a COPY is indistinguishable from a hand-written skill — without metadata
there is no uninstall listing, no status, no drift detection. Two stores
with strictly split roles, both **never committed to git**:

1. **Per-dest manifest** — `.meta-skills.json` in each product's skills
   dir *(implemented)*. The single source of truth for "what is installed
   here": skill id, method, source rev, installed_at. Travels with the
   install; survives this repo being re-cloned or moved. Kept out of git
   by the skills dir's manager-owned `.gitignore` (see special rule 1).
2. **Dest index** — a local, gitignored file in this clone *(pending)*.
   Stores *only the list of dest paths ever installed to* — deliberately
   no per-skill data, so the two stores cannot desync. Enables
   `status --all`, bulk re-install after a submodule bump, and
   dangling-symlink cleanup. Stale paths get pruned on read; a lost index
   rebuilds itself as dests are touched again.

Known limitation (accepted): a COPY committed into a dest repo and cloned
on another machine has no provenance there — drift detection only works on
the machine that installed. If that ever matters, the opt-in exception is
a small provenance file committed *inside* the copy (vendoring-note
style); skipped for now.

## use cases

### UC1 — browse what's available

`list` shows every collection and its skills. Uninitialized submodules are
listed with the exact init command instead of being omitted.

### UC2 — interactive install (the wizard)

`install` with no arguments, in a TTY: checkbox-pick skills (grouped by
collection) → dest path (defaults to cwd) → product multi-select
(configured ones pre-checked) → method select (pre-set to the per-root
default) → a plan preview showing every `skill → target` line plus all
special-rule warnings → confirm → install. Ctrl-C anywhere aborts cleanly
with nothing half-done before the confirm.

### UC3 — scripted install

`install <skill>... --dest <path> --product <p> --method <m> --yes` runs
with zero prompts. Skill arguments accept exact id (`my/foo`), exact name,
or unique substring; ambiguity is an error listing the matches. Without a
TTY, anything that would prompt fails loudly instead — a script never
blocks and never gets a silent guess.

### UC4 — evaluate a foreign skill inside a work repo

Symlink an EXTERNAL skill into a REPO dest. The manager warns this is
evaluation-only and keeps the link transient (skills-dir `.gitignore`) so
`git status` in the work repo stays clean and collaborators are
unaffected. When done: `uninstall` removes link + record + ignore line; or
adopt for real (UC5).

### UC5 — adopt a skill permanently in a shared repo

COPY into the REPO dest (the default there). The snapshot is committed by
the user as normal repo content; provenance goes to the local manifest
(not committed). Re-running install on an existing target refuses unless
`--force`.

### UC6 — detect drift after updating sources

After `git pull` / submodule bump in this repo, `status --dest <path>`
reads each product manifest at the dest and reports per skill: `ok`,
`drifted` (source rev changed since install), or `source gone` (skill no
longer exists here). Eventually `status --all` does this across every
known dest via the dest index, and offers re-install of drifted copies.

### UC7 — uninstall

`uninstall` with no names, in a TTY: checkbox over everything the dest's
manifests record (across all product dirs, labeled per product). With
names: removes those recorded entries. Either way the full target paths
are shown and confirmed (default **no**) before anything is deleted;
manifest records go with the files.

### UC8 — install a CUSTOM upstream

If an upstream ships its own installer, plain COPY/SYMLINK may be wrong.
`--method custom` runs the rewiring registered for that collection at its
current pinned rev. No registered rewiring for `(collection, rev)` — for
example right after bumping the submodule — is a hard error telling the
user the rewiring must be revisited.

### UC9 — one dest, several products

A dest root that serves several agents (e.g. a repo with both `.claude/`
and `.codex/`) gets the skill installed per selected product, each with
its own manifest. Note omp reads `.claude`/`.codex` project dirs by
itself, so a claude install often covers omp at project level (see
`skill-dirs.md`).

### UC10 — bulk operations over all dests *(pending, needs dest index)*

"Show every place I've installed to, and what drifted" — `status --all`.
"Submodule X got bumped; refresh every copy of its skills" — iterate the
dest index, re-install drifted entries after one confirmation. "Find
symlinks whose target vanished" — cleanup listing.

## open questions

- Should the wizard offer creating a product dir at a root that has none
  (first install into a fresh repo), or is the explicit product select
  consent enough? (current behavior: selecting a product creates its dir)
- Additional read-only conventions to *discover* but never install into:
  `.github/skills/`, plugin dirs, Codex `.system`.
- Whether OWN skills should also be versioned per-skill (currently repo
  HEAD is the rev for all of `my/`).
