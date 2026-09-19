---
name: journal-search
description: "Search past journal entries to answer questions about previous sessions — what was done, what was discovered, what changed, and what's still open."
allowed-tools: [Read, Glob, Grep, Bash]
---

# journal-search — Answer Questions from Past Journals

Search and synthesize information from journal entries in `journals/` to answer the user's question about previous work sessions.

## Steps

### 1. Understand the question

Identify what the user is asking about. Common queries:

- **What/when**: "What did we do about X?", "When did we change Y?"
- **Why**: "Why is Z implemented this way?"
- **Discoveries**: "What gotchas did we find about X?"
- **Open threads**: "What's left unfinished?"
- **Changes**: "What files were touched for feature X?"

### 2. Search journals

Journals live in `journals/*.md` and have YAML frontmatter with `date`, `branch`, `host`, `user`, `tldr`. The session PID is encoded in the filename (`YYYYMMDD-p{PID}-{topic}.md`), not in frontmatter.

#### Strategy

0. **Start with the index** — `journals/index.md` catalogs every journal, one line
   each, grouped by theme. Skim the relevant group(s) first; it's often enough to
   identify the right files without grepping. (Superset/AI-BI journals are separate:
   `deps/superset/journals/` + index `deps/superset/doc/index-superset.md`.)
   Prefer `git grep` over plain grep when possible.

1. **Then grep** — search for keywords from the user's question across all journals:
   ```
   grep -li <keyword> journals/*.md
   ```
   Use multiple keywords in parallel if the question has several concepts.

2. **If grep finds matches**, read the matching files. Start with frontmatter + title (first ~10 lines) to assess relevance, then read the full file for relevant ones.

3. **If grep finds nothing**, broaden: try synonyms, related terms, or list all journals and scan their `tldr` fields:
   ```
   grep "^tldr:" journals/*.md
   ```

4. **For time-based queries** ("last week", "recently"), list journals sorted by date and read the most recent ones:
   ```
   ls -t journals/*.md
   ```

### 3. Synthesize an answer

- Answer the user's question directly, citing specific journal entries by filename and section.
- Use `journals/filename.md` references so the user can find the source.
- If the answer spans multiple sessions, present it chronologically.
- If journals contain contradictory information, flag it — the more recent entry is likely more accurate.
- If no journals are relevant, say so clearly rather than guessing.

### 4. Guidelines

- Be concise. The user wants an answer, not a journal dump.
- Quote specific discoveries/quirks verbatim when they're the answer — these are the high-value bits.
- If the question is about open threads, check whether later journals resolved them.
- Don't fabricate information that isn't in the journals. If the journals don't cover the topic, say so.
