# Mining cookbook

How to extract workflow signals from records. Sources are unbounded — anything that records behavior over time is minable. This file is **append-only knowledge**: when a run mines a source family not covered below, add a recipe section for it.

## Generic procedure (any unfamiliar source)

1. **Sample before reading.** Look at a few records to learn the shape: what is one record, where are the timestamp, the actor, and the action? Large sources are never read whole — filter and aggregate (`jq`, `grep`, `awk`, a throwaway script, or subagents).
2. **Cut to the window.** Restrict to records since the last run (journal date). File mtimes (`find -newermt`), in-record timestamps, or export date ranges.
3. **Normalize to events.** Reduce records to `(when, who, what, outcome)` tuples — enough to count and cluster, nothing more.
4. **Apply the signal table** from `SKILL.md` Step 1: repetition, constant answers, corrections, kept deviations, skipped steps, rubber-stamp approvals, re-explained context, by-hand sequences.
5. **Keep pointers.** Every signal cites its source (file, message id, commit hash, page) so proposals can show evidence.

Scaling: more than ~10 files or a very large export → fan out subagents, one per file/chunk, each returning only a compact list of `{signal, quote, source, kind}` — never raw content. Dedup and cluster in the main context.

Privacy: treat every source as sensitive. Ask before touching anything not explicitly offered (e.g. shell history, mail), and quote the minimum needed as evidence.

## Recipes by source family

### User-provided documents & notes

Notes, TODO lists, wikis, photographed paper, PDFs. Read directly (or via subagents for bulk). Watch for: TODO items recurring across dates (a routine trying to exist), "how to do X" notes duplicating each other (merge candidates), instructions written down but contradicted by later records. Opinions found in writing ("I should always...") count as **opinions, not facts** — confirm in the grilling step before codifying.

### Chat & message exports

Slack/LINE/WeChat/Discord exports, email mbox, support threads. Identify the export's record separator and timestamp format first (generic procedure). Cluster by counterpart and by recurring phrases; corrections and repeated explanations to other people are strong rule candidates. Language cues for corrections vary — use the languages actually in the data (e.g. English: "no," / "actually" / "instead"; Japanese: 違う, じゃなくて; Chinese: 不对, 不是).

### Git history

Routine-work discovery — cluster commit subjects:
```sh
git -C "$REPO" log --since="$LAST_RUN_DATE" --format='%s' |
  sed 's/[0-9,]\+//g' | sort | uniq -c | sort -rn | head -20
```
High-count clusters of similar messages = recurring task; check whether written guidance already covers it and whether that guidance was followed.

Repeated co-edited file sets (a change ritual worth documenting):
```sh
git -C "$REPO" log --since="$LAST_RUN_DATE" --name-only --format='---' |
  awk 'BEGIN{RS="---"} NF' | sort | uniq -c | sort -rn | head
```

### Shell history

Only with permission. `~/.zsh_history` / `~/.bash_history`: strip timestamps, count normalized commands (`sort | uniq -c | sort -rn`). Long pipelines appearing repeatedly are script candidates; `cd A && cmd1; cmd2; cmd3` rituals are checklist/script candidates.

### Claude Code session transcripts

Location: `~/.claude/projects/<cwd-slug>/*.jsonl` where the slug is the project's absolute path with `/` replaced by `-`. One file per session, named by session UUID. Line format: JSON objects with a `type` field:

- `type=="user"` — user messages. `message.content` is a **string** for typed text, an **array** for tool results; filter to strings for what the user actually said.
- `type=="assistant"` — `message.content[]` blocks: `type=="text"` prose, `type=="tool_use"` with `.name`/`.input`.
- `isSidechain==true` — subagent traffic; usually skip. `type=="summary"` — compaction summaries, a cheap session précis.

Sessions in the window, newest first:
```sh
find ~/.claude/projects/*/ -name '*.jsonl' -newermt "$LAST_RUN_DATE" | xargs ls -t
```

Everything the user typed (requests, answers, corrections):
```sh
jq -r 'select(.type=="user" and (.message.content|type=="string")) | .message.content' S.jsonl
```
Lines starting with `<` are harness/command wrappers, not user prose; `<command-name>` lines show which skills were invoked.

Questions the assistant asked (promotion candidates when answers repeat):
```sh
jq -r 'select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="AskUserQuestion") | .input.questions[].question' S.jsonl
```

Command frequency across sessions (by-hand sequences → script/skill candidates):
```sh
jq -r 'select(.type=="assistant") | .message.content[]? |
  select(.type=="tool_use" and .name=="Bash") | .input.command' *.jsonl |
  sort | uniq -c | sort -rn | head -30
```

Correction hunting — grep user text for cue words, then read surrounding lines for context; a keyword alone is not a correction.

### App / server / device logs, structured data

CSV, ledgers, calendars, tickets, analytics exports. Aggregate by actor+action+period; recurring manual interventions in otherwise-automated flows are the top signal (each intervention is a missing rule or a broken step).
