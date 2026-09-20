# Categorizing external collections (as of 2026-09)

Before taking an upstream on, read its *shape*: the shape decides how it
gets vendored and installed, not taste. `SPEC.md` defines the three
sources and the three methods; this file is the procedure for picking, plus
the per-collection notes that result. Most shapes end in a submodule; one
(E) ends in a recipe and an extraction instead.

## three questions

1. **Where does `SKILL.md` live?** Repo root (one-skill repo), `skills/<name>/`
   (library layout), top-level dirs (`<repo>/<name>/SKILL.md`), or nested
   groups (only pi reads those — we install flat regardless).
2. **Is the skill dir self-contained?** Does it carry everything it needs, or
   does it reach outside itself — `../lib`, `$CLAUDE_PLUGIN_ROOT`, a
   `package.json` runtime dep, an MCP server, a `.tmpl` waiting for an
   installer?
3. **Does upstream ship its own install story, and does that story add
   *behavior*?** Plugin/marketplace manifests that merely repackage the same
   files change nothing for us. Hooks, slash commands, extensions and MCP
   servers do — that's the part a skills-dir install cannot carry.

Cheap check for question 2:

```sh
grep -rn 'PLUGIN_ROOT\|\.\./' <collection>/skills
```

## the five shapes

**A — plain library.** `skills/<name>/SKILL.md`, self-contained; any plugin
manifest is just another route to the same files. → normal install: SYMLINK
for HOME/DIR dests, COPY for REPO. Nothing is lost.
*Seen in:* `mattpocock/skills`.

**B — plugin with a skill core.** The skills are self-contained, but the repo
also ships hooks / commands / per-product extensions around them. → still a
normal install, *plus* a recorded delta: what the native plugin route adds
that we don't get. Decide explicitly whether that delta matters; don't
discover it later.
*Seen in:* `ayghri/i-have-adhd`, `DietrichGebert/ponytail`, `obra/superpowers`.

**C — toolkit.** Skills aren't separable from the repo: `bin/`, shared
`lib/`, runtime deps, a `setup` that wires paths, templates instantiated at
install time. → CUSTOM, a rewiring in `rewire.py` pinned to `(collection,
rev)`. A flat copy here produces a skill that references files that aren't
there.
*Seen in:* `garrytan/gstack` (top-level skill dirs + root `SKILL.md`
alongside `SKILL.md.tmpl`, `setup`, `bin/`, bun deps).

**D — single file.** A gist or a lone root `SKILL.md`. Discovery treats the
collection root as the skill, so the installed name is the *submodule dir
name* — pick that path deliberately when adding the submodule.
*Seen in:* `k16shikano/ja-tech-writing`.

**E — monorepo catalogue.** A product repo that happens to contain
hundreds of bundles. Two things break at once: it is too big to vendor,
and its tree is not a library — several registries hold the same bundles,
a large share of the entries are frontmatter pointing at an upstream we do
not have, bundles reach each other by relative path, and the best material
may not be in skill form at all. → REMOTE: pin a rev in `recipes.py`,
fetch a sparse slice into `.cache/`, and derive `build/<collection>/` with
`./cli extract`. No submodule, nothing vendored, nothing hand-curated.
*Seen in:* `nexu-io/open-design`.

Telling E from A is a size-and-duplication question, not a taste one:

```sh
gh api repos/<owner>/<repo> --jq .size          # KB; five figures is a warning
find <collection> -name SKILL.md | wc -l        # vs. how many are distinct
find <collection> -name SKILL.md | xargs -n1 dirname | xargs -n1 basename \
  | sort | uniq -d | wc -l                      # duplicate basenames
```

Wrinkle: a repo with both a root `SKILL.md` and per-skill dirs (gstack) is
discovered as both — the root entry is usually a router/overview, not an
installable skill. Check before installing it.

## per-collection notes

### `ayghri/i-have-adhd` — shape B, normal install

Pinned rev `839872f`. Skill: `skills/i-have-adhd/` — `SKILL.md` plus
`agents/{gemini.toml,openai.yaml}` sidecars, no path escapes, so a dir
copy is faithful. `.cursor/skills/i-have-adhd/SKILL.md` is byte-identical
and lives under a dot-dir, which discovery prunes — no duplicate entry.

What the native plugin route
(`claude plugin marketplace add ayghri/i-have-adhd`) adds and we don't get:

- a `SessionStart` hook (`hooks/always-on.mjs`, resolved via
  `CLAUDE_PLUGIN_ROOT`) that loads the ruleset automatically when the flag
  file `~/.claude/.i-have-adhd-always` exists;
- the opencode command/plugin and the pi/omp TypeScript extension wiring.

What we don't lose: the frontmatter sets `disable-model-invocation: true`,
so the skill is meant to fire on `/i-have-adhd` anyway — and a plain
`.claude/skills/` install already provides that invocation.

Verdict: install as a normal skill; the only casualty is the *optional*
always-on hook. If I want always-on without the plugin, the equivalent is
pasting the ruleset into `CLAUDE.md`/`AGENTS.md` — which is exactly what
upstream's `INSTALL.md` documents for products without plugin support. No
rewiring registered.

### `nexu-io/open-design` — shape E, REMOTE + extraction

Pinned rev `f5707c8` in `recipes.py`. OpenDesign is a local-first design
workspace (Next.js UI → Express daemon → a CLI agent it spawns), Apache-2.0,
**3.5 GB** with ~300 PRs a week. What we want from it is content, not the
product: the daemon composes a large system prompt from a design system, a
skill body, and craft references, but none of that runs here.

Why it cannot be a normal collection:

- A naive walk finds **536 `SKILL.md` dirs**. 254 of them are under
  `plugins/`, which re-packages 141 bundles that already exist under
  `skills/` and `design-templates/` — flat install would collide.
- **85 of 163** `skills/` entries are catalogue stubs: frontmatter plus
  "install the upstream bundle yourself". Discoverable names with nothing
  behind them, which is worse than absent.
- 39 bundles reach a master bundle by `../html-ppt/…`. Flat install keeps
  those working (siblings), but only if the target is extracted too — and
  only if we never rename a directory.
- 12 bundles declare a frontmatter `name` that differs from their dir; 4
  have no description. Products key on `name`, so both must be fixed.
- `craft/*.md` is injected at runtime by their daemon from
  `od.craft.requires`. Outside the app it is simply lost unless inlined.
- `design-systems/` — 153 packages of `DESIGN.md` + tokens, the single
  richest thing in the repo — contains **no `SKILL.md` at all**, so a
  plain extraction walks straight past it. We synthesize a router bundle.
- `design-templates/open-design-landing` is 22 MB of their own marketing
  PNGs. Denylisted; bundles that merely mention it keep their content and
  get the dead link defused.

What the native route (`claude plugin marketplace add nexu-io/open-design`)
adds and we don't get: an MCP server over their `od` daemon — projects,
files, previews, live artifacts. That is the product, and skipping it is
the point. What we lose with it: their prompt composer (the "expert
designer" charter, the discovery/question-form layer, the direction
library, the deck framework contract). Those live in
`apps/daemon/src/prompts/` as Apache-2.0 TypeScript, not as skills — worth
reading, not installable.

Attribution is not one line: 189 bundles declare an `od.upstream` across
92 distinct third-party repos, and 53 carry their own LICENSE. The
extractor carries each bundle's license (or the repo's) and writes an
`ATTRIBUTION.md` per bundle recording origin, rev, declared upstream, and
every modification we made. The design systems are interpretations of
public brand languages — Apache-2.0 covers the prose, not the trademarks.

Current result: **191 extracted + 1 generated, 86 dropped, ~26 MB**. See
`docs/extracts/nexu-io-open-design.md`, which the extractor rewrites on
every run.

### others

Not yet categorized beyond the shape guesses above — those submodules are
uninitialized. Categorize on first use, and add the note here.
