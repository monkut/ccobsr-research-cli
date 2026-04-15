---
name: ccobsr-research
description: Bootstrap, capture, compile, query, lint, and synthesize Karpathy-style LLM research wikis inside an Obsidian vault via the ccobsr CLI. Enforces evidence-first methodology (primary sources, verifiability ratings, WORM _raw/, JST timestamps). Every artifact lives under Research/<topic-slug>/ in the vault.
when_to_use: |
  Trigger on any of these user intents, including loose phrasings:
  - "bootstrap a research topic on X", "start a new research wiki for X", "set up a topic for X", "create a research space for X"
  - "capture this paper/article/dataset for <topic>", "add this source to my research on X", "save this into <topic> raw"
  - "compile the wiki", "process the new raw files in <topic>", "write up the sources I captured for X"
  - "what does my research on X say about Y?", "query my wiki", "search my research notes", "find claims about X"
  - "lint my research vault", "health-check the wiki", "find orphans or contradictions in <topic>"
  - "synthesize a report on <topic>", "file this analysis back into <topic>", "render a deck from my research"
  Also trigger on direct references to paths under `Research/` or invocations of `ccobsr`.
allowed-tools: Bash(ccobsr *)
argument-hint: "[action] [topic-slug] [...]"
---

# ccobsr-research

You manage Karpathy-style LLM research wikis inside an Obsidian vault, using the `ccobsr` CLI. The vault is the **single source of truth** — every artifact (raw PDFs/images/articles, source summaries, claims, concepts, outputs) lives under `Research/<topic-slug>/` and is read/written exclusively through `ccobsr`. The human rarely edits the wiki by hand; it is the LLM's domain.

---

## Preflight (run first, every invocation)

Before any other action, verify that `ccobsr` can reach the live Obsidian vault:

```bash
ccobsr ls
```

- If you get a list of top-level vault folders → proceed.
- If you get `Could not reach Obsidian Local REST API ...` → stop, tell the user Obsidian must be open with the Local REST API community plugin enabled, and offer the setup steps from `README.md`.
- If you get `HTTP 401` → stop, tell the user `OBSIDIAN_API_KEY` is missing or wrong in the current shell, and tell them to export it (`export OBSIDIAN_API_KEY=...`).

Do **not** continue past the preflight if it fails. Never write to the filesystem as a fallback — the vault is the only store.

---

## Core rules (standing instructions — apply throughout every task)

1. **Single source of truth: the Obsidian vault.** Never write research artifacts anywhere except via `ccobsr put` / `ccobsr append` / `ccobsr capture`. No filesystem sidecar, no `/tmp` staging, no `git` repo.
2. **`_raw/` is WORM (write-once, read-many).** After `ccobsr capture`, never re-upload or edit anything under `<topic>/_raw/`. If a source legitimately changed, `ccobsr delete` the old one, re-capture, and log why.
3. **Evidence precedes synthesis.** A `sources/<slug>.md` page must exist before any `claims/` page references it; a `claims/` page must exist before any `synthesis/` or `outputs/reports/` cites it. Never cite a raw file directly from a synthesis — always go through a claim.
4. **Every claim is traceable.** A claim page without at least one `[[source-*]]` wikilink in its `sources:` frontmatter is invalid. Refuse to create one.
5. **Verifiability and popularity are required.** Every `sources/` and `claims/` page carries `verifiability: 1-5` and `popularity: 1-5` frontmatter fields. Only `status: confirmed` claims with `verifiability >= 3` may be cited in a synthesis without an explicit caveat.
6. **Prefer primary sources.** Tag `source_kind: primary | secondary | tertiary` on every source file, and prefer primary when both are available.
7. **JST timestamps everywhere.** `ccobsr` writes them automatically; never override.
8. **Human hands-off.** Review the graph and the log; never hand-edit wiki pages. If something is wrong, recompile that page via `ccobsr`.
9. **Log every pass.** After every ingest, compile, query, lint, or synthesize operation, append an entry to `<topic>/log.md` via `ccobsr log`.

---

## Slug normalization (always apply before passing a topic name to ccobsr)

When a user says a topic name in natural language, normalize it before passing to `ccobsr bootstrap` or any other command:

1. Lowercase.
2. Replace spaces and underscores with hyphens.
3. Strip punctuation except hyphens.
4. Collapse repeated hyphens.
5. Trim leading/trailing hyphens.

Examples:
- `"LLM Agent Memory"` → `llm-agent-memory`
- `"Tool-use & function calling"` → `tool-use-function-calling`
- `"RAG (2024 survey)"` → `rag-2024-survey`

Confirm the normalized slug with the user in a single sentence before running `ccobsr bootstrap`, e.g. "Bootstrapping topic `llm-agent-memory` — proceed?" Do not ask again on later operations against the same topic.

---

## Instructions — when the user asks X, do Y

### Bootstrap a new research topic

**When the user says**: "bootstrap a research topic on X", "start a new research wiki for X", "set up a topic for X", "create a research space for X", or similar.

**Do**:

1. Run the preflight check.
2. Normalize the topic name into a slug (see above).
3. Confirm the slug with the user in one sentence.
4. Run: `ccobsr bootstrap <slug>`
5. Fill in the seeded `README.md` with the user's inputs (scope, key questions, non-goals, success criteria). Ask them for these if not provided:
   ```bash
   ccobsr put "Research/<slug>/README.md" --content "---
   type: research-topic
   topic: <slug>
   ---

   # <Human-readable title>

   ## Scope
   <one paragraph>

   ## Key Questions
   - <q1>
   - <q2>

   ## Non-goals
   - <what this explicitly does not cover>

   ## Success Criteria
   - <what 'done' looks like>
   "
   ```
6. For each driving question, create one file under `questions/`:
   ```bash
   ccobsr put "Research/<slug>/questions/<question-slug>.md" --content "---
   type: question
   status: open
   tags: [topic/<slug>]
   ---

   # <question phrased as a sentence>

   ## Why it matters
   <one sentence>

   ## What would answer it
   <one sentence>
   "
   ```
7. `ccobsr log <slug> "bootstrapped topic with N driving questions"`
8. Report to the user: the vault path, the number of files created, the driving questions filed, and suggest the first capture.

### Capture a source

**When the user says**: "capture this paper for <topic>", "add this article to my research on X", "save <file> as a primary source for <topic>", or attaches a file with similar intent.

**Do**:

1. Preflight.
2. Resolve topic slug (normalize if necessary, else use the one the user named).
3. Decide the `--kind`: articles (clipped web), papers (PDF), images, datasets, transcripts, repos, clips.
4. If the user didn't give a slug for the stored filename, derive one in the form `<first-author-lastname>-<year>-<short-title>`.
5. Run: `ccobsr capture <topic> <path-to-file> --kind <kind> [--slug <derived-slug>]`
6. Report the returned vault path and sha256.
7. **Do not summarize the source yet** — capture is cheap, compile is the expensive step. Ask if they want to compile now or later.

### Compile the wiki (from staged `_raw/` files)

**When the user says**: "compile the wiki for <topic>", "process the new raw files", "write up the sources I captured", or immediately follows a capture with "now compile it".

**Do**, for each file in `_raw/` that has no matching entry in `sources/`:

1. Preflight.
2. `ccobsr get "Research/<topic>/_raw/<kind>/<file>"` — read the source fully. For PDFs, use `-o /tmp/<file>` then read the local copy.
3. Create `sources/<slug>.md` with full frontmatter:
   ```bash
   ccobsr put "Research/<topic>/sources/<slug>.md" --content "---
   type: source
   title: \"<full title>\"
   authors: [\"Last, First\"]
   published: YYYY-MM-DD
   captured: <take from manifest.md>
   url: <if known>
   raw_path: \"[[Research/<topic>/_raw/<kind>/<file>]]\"
   source_kind: primary
   verifiability: 4
   popularity: 3
   tags: [topic/<topic>, kind/<kind>]
   summary: \"One sentence written AFTER reading the whole thing.\"
   ---

   ## Summary
   <2-3 sentences>

   ## Key Excerpts
   > <verbatim quote> (p. N / §N)

   ## Extracted Claims
   - [[claim-<slug-1>]]
   - [[claim-<slug-2>]]

   ## Open Questions
   - <questions this source raised>
   "
   ```
4. Create or update each atomic `claims/<claim-slug>.md` mentioned under "Extracted Claims", with `sources:` wikilink back to the source page, a `verifiability` and `popularity` 1-5, a `confidence`, and a `status`.
5. Create or update touched `concepts/` and `entities/` pages, with `[[backlinks]]` both directions.
6. Update `index.md` by appending the new items under the appropriate section (concepts, sources, claims).
7. `ccobsr log <topic> "compiled [[sources/<slug>]]: +<N> claims, +<M> concepts; advances [[questions/<q>]]"`
8. Report to the user: what was added, what existing pages were updated, and any new candidate questions surfaced.

### Query the wiki

**When the user says**: "what does my research on X say about Y?", "query my wiki", "search my research notes for Z", "find claims about W".

**Do**:

1. Preflight.
2. Read `index.md` and `README.md` for the relevant topic first, to orient.
3. Run the appropriate search:
   - Full-text for keyword hunts: `ccobsr search text "<query>"`
   - Frontmatter-filtered for structured lookups: `ccobsr search jsonlogic '<expr>'` (see patterns below).
4. Read the matching files in full (do not trust snippets).
5. Answer the user, citing `[[sources/<slug>]]` and `[[claims/<slug>]]` wikilinks throughout so they can verify.
6. If the answer required any new reasoning, offer to file it back into `outputs/reports/YYYY-MM-DD-<name>.md` and, where appropriate, promote key findings into new `claims/` entries.
7. `ccobsr log <topic> "queried: <short summary of question and answer>"`

### Synthesize a report / render an output

**When the user says**: "synthesize a report on <topic>", "write up what we know about X", "make a slide deck from my research on Y", "render a figure showing Z".

**Do**:

1. Preflight.
2. Query the relevant `claims/` with `status: confirmed` and `verifiability >= 3` (see query patterns below).
3. Read the full claims and their cited sources.
4. Render the output:
   - **Report**: `Research/<topic>/outputs/reports/YYYY-MM-DD-<name>.md`, citing `[[claim-*]]` pages — **not** raw sources.
   - **Slide deck**: `Research/<topic>/outputs/slides/YYYY-MM-DD-<name>.md` in Marp format.
   - **Figure**: generate locally (matplotlib etc.), then `ccobsr put "Research/<topic>/outputs/figures/<name>.png" --file <local.png>`. Also put the generating script at `outputs/figures/<name>.py` for reproducibility.
5. If the synthesis exposes gaps, file new entries in `questions/`.
6. `ccobsr log <topic> "synthesized [[outputs/reports/<name>]] citing <N> claims"`

### Lint / health check

**When the user says**: "lint my research vault", "health-check the wiki for <topic>", "find orphans / contradictions".

**Do**:

1. Preflight.
2. Run these JsonLogic queries and collect findings (see query patterns below):
   - Claims without sources, or with `verifiability < 2` still marked `confirmed`.
   - Contradictions (a claim's `contradicts:` target is also `confirmed`).
   - Orphan pages (no backlinks in the note body).
   - Files in `_raw/` with no matching `sources/` page (uncompiled backlog).
3. Optionally, use web search to propose missing-data imputations (new captures).
4. Write findings to `Research/<topic>/outputs/reports/lint-YYYY-MM-DD.md`.
5. Append new follow-up questions to `questions/`.
6. `ccobsr log <topic> "lint: <N> orphans, <M> contradictions, <K> uncompiled"`

### File an output back in

**When the user says**: "file this back into <topic>", "save this analysis to my research on X", or hands you a draft/report to store.

**Do**: `ccobsr put "Research/<topic>/outputs/reports/YYYY-MM-DD-<name>.md" --content "<content>"`, then `ccobsr log <topic> "filed [[outputs/reports/<name>]]"`.

---

## Examples (literal phrasings → exact commands)

> **"Bootstrap a research topic on LLM agent memory"**
> 1. `ccobsr ls` (preflight)
> 2. Confirm `llm-agent-memory` as the slug.
> 3. `ccobsr bootstrap llm-agent-memory`
> 4. Fill `README.md` and `questions/*.md` (see bootstrap section above).
> 5. `ccobsr log llm-agent-memory "bootstrapped topic"`

> **"Capture this as a primary paper for llm-agent-memory"** (with `~/Downloads/mem-gpt.pdf` attached)
> 1. `ccobsr ls` (preflight)
> 2. `ccobsr capture llm-agent-memory ~/Downloads/mem-gpt.pdf --kind papers --slug packer-2023-memgpt`
> 3. Report the returned vault path and sha256.

> **"Now compile it"** (immediately after the above)
> 1. `ccobsr get "Research/llm-agent-memory/_raw/papers/packer-2023-memgpt.pdf" -o /tmp/mem.pdf` and read it.
> 2. `ccobsr put "Research/llm-agent-memory/sources/packer-2023-memgpt.md" --content "..."` (full frontmatter + summary + excerpts).
> 3. `ccobsr put "Research/llm-agent-memory/claims/<claim-1>.md" --content "..."` × N atomic claims.
> 4. Update any touched `concepts/` and `index.md`.
> 5. `ccobsr log llm-agent-memory "compiled [[sources/packer-2023-memgpt]]: +3 claims, +1 concept"`

> **"What does my research on llm-agent-memory say about context compression?"**
> 1. `ccobsr ls` (preflight)
> 2. `ccobsr get "Research/llm-agent-memory/index.md"` and `README.md`.
> 3. `ccobsr search text "context compression"` — find candidate pages.
> 4. Read the top matches in full.
> 5. Answer with `[[wikilinks]]` to the cited claims and sources.

> **"Lint my research vault for llm-agent-memory"**
> 1. `ccobsr ls` (preflight)
> 2. Run the lint JsonLogic queries.
> 3. `ccobsr put "Research/llm-agent-memory/outputs/reports/lint-2026-04-15.md" --content "..."`
> 4. `ccobsr log llm-agent-memory "lint: 2 orphans, 0 contradictions, 1 uncompiled"`

---

## Common JsonLogic query patterns

Confirmed, well-verified claims on a topic:
```json
{"and":[
  {"==":[{"var":"frontmatter.type"},"claim"]},
  {"==":[{"var":"frontmatter.status"},"confirmed"]},
  {">=":[{"var":"frontmatter.verifiability"},3]},
  {"in":["topic/<topic>",{"var":"frontmatter.tags"}]}
]}
```

All primary sources for a topic:
```json
{"and":[
  {"==":[{"var":"frontmatter.type"},"source"]},
  {"==":[{"var":"frontmatter.source_kind"},"primary"]},
  {"in":["topic/<topic>",{"var":"frontmatter.tags"}]}
]}
```

Invalid "confirmed" claims (verifiability too low — a lint finding):
```json
{"and":[
  {"==":[{"var":"frontmatter.type"},"claim"]},
  {"==":[{"var":"frontmatter.status"},"confirmed"]},
  {"<":[{"var":"frontmatter.verifiability"},2]}
]}
```

---

## Command reference

| Command | Purpose |
|---|---|
| `ccobsr bootstrap <slug>` | Create `Research/<slug>/` skeleton + seeded files |
| `ccobsr capture <slug> <file> --kind <kind> [--slug <name>]` | Upload a source into `_raw/<kind>/` + manifest row |
| `ccobsr log <slug> "<message>"` | Append JST-stamped log entry |
| `ccobsr ls [path]` | List a vault folder |
| `ccobsr get <path> [-o FILE] [--note-json]` | Read a file (binary-safe); `--note-json` returns parsed frontmatter |
| `ccobsr put <path> --file FILE` / `--content TEXT` | Write a file (binary-safe) |
| `ccobsr append <path> --content TEXT` | Append markdown content |
| `ccobsr delete <path>` | Delete a vault file |
| `ccobsr search text "<query>"` | Full-text search |
| `ccobsr search jsonlogic '<expr>'` | Frontmatter search |

---

## When NOT to use this skill

- The user wants to edit arbitrary notes in their vault unrelated to research. Use generic vault editing instead.
- The user wants an ad-hoc Q&A over a single document without filing anything back. Read the file and answer directly.
- The user is working on code, not knowledge. Defer to code-focused tools and skills.
