---
name: ccobsr-research
description: Manage Karpathy-style LLM research wikis stored in Obsidian via the ccobsr CLI. Use when the user asks to bootstrap a research topic, capture a source, compile or query a research wiki, or file outputs back into the vault. Enforces evidence-first methodology (primary sources, verifiability ratings, JST timestamps, WORM _raw/).
---

# ccobsr-research

Use the `ccobsr` CLI to manage research topics as markdown wikis inside an Obsidian vault. The vault is the **single source of truth** — every artifact (raw PDFs, images, source summaries, claims, outputs) lives under `Research/<topic-slug>/` and is written via the Obsidian Local REST API. The human rarely edits the wiki directly; it is the LLM's domain.

## Prerequisites

- Obsidian running with the **Local REST API** community plugin enabled.
- Environment variables set:
  - `OBSIDIAN_API_URL` (default `https://127.0.0.1:27124`)
  - `OBSIDIAN_API_KEY` (from the plugin settings)
- `ccobsr` installed on PATH (`uv tool install ccobsr-research-cli` or equivalent).

## Core rules (non-negotiable)

1. **Single source of truth: the Obsidian vault.** Never write research artifacts to the local filesystem as a sidecar. Every `PUT`/`POST` goes through `ccobsr`.
2. **`_raw/` is WORM.** After `ccobsr capture`, do not re-upload or edit anything under `<topic>/_raw/`. If a source legitimately changed, delete + re-capture and log why.
3. **Evidence precedes synthesis.** Create `sources/<slug>.md` before writing any `claims/` or `synthesis/` that references it. Never cite a raw file directly from a synthesis — always go through a claim.
4. **Every claim is traceable.** A claim page without at least one `[[source-*]]` wikilink in its `sources:` frontmatter is invalid.
5. **Verifiability and popularity are required.** Every `sources/` and `claims/` page carries `verifiability: 1-5` and `popularity: 1-5` frontmatter fields. Only `status: confirmed` claims with `verifiability >= 3` may be cited in a synthesis without an explicit caveat.
6. **JST timestamps everywhere.** `ccobsr` writes them; do not override.
7. **Prefer primary sources.** Tag `source_kind: primary | secondary | tertiary` on every source file.
8. **Human hands-off.** Review the graph and the log; do not hand-edit wiki pages. If something is wrong, recompile.

## Command reference

### Topic bootstrap

```bash
ccobsr bootstrap <topic-slug>
```

Creates `Research/<topic-slug>/` with the full folder skeleton (`_raw/`, `sources/`, `claims/`, `concepts/`, `entities/`, `comparisons/`, `questions/`, `synthesis/`, `outputs/`, `_meta/`) plus seeded `README.md`, `index.md`, `log.md`, `_meta/manifest.md`, and `_meta/taxonomy.md`.

After bootstrapping, immediately fill in `README.md` (scope, key questions, non-goals, success criteria) and seed `questions/` with the driving questions — one file per question.

### Capture a source

```bash
ccobsr capture <topic-slug> <path-to-file> --kind {articles,papers,images,datasets,transcripts,repos,clips}
```

Uploads the file as raw bytes (PDFs, PNGs, CSVs all work), appends a row to `_meta/manifest.md` with sha256 + timestamp, and logs the capture. **Do not summarize yet** — capture is cheap.

### Compile (LLM-run, after capture)

This is the "compile the wiki" step. For each newly captured file:

1. `ccobsr get Research/<topic>/_raw/<kind>/<file>` — read the source.
2. Create `sources/<slug>.md` (one-sentence summary + key excerpts + frontmatter):
   ```bash
   ccobsr put Research/<topic>/sources/<slug>.md --content "---
   type: source
   title: \"...\"
   authors: [\"...\"]
   published: YYYY-MM-DD
   captured: <JST timestamp>
   url: ...
   raw_path: \"[[Research/<topic>/_raw/<kind>/<file>]]\"
   source_kind: primary
   verifiability: 4
   popularity: 3
   tags: [topic/<topic>, kind/<kind>]
   summary: \"One sentence.\"
   ---

   ## Summary
   ..."
   ```
3. Extract atomic claims → `ccobsr put Research/<topic>/claims/<claim-slug>.md ...` with `sources: [[source-slug]]` in frontmatter.
4. Create/update `concepts/` and `entities/` touched by the source.
5. `ccobsr log <topic> "compiled [[source-slug]]: +N claims, +M concepts, advances [[question-slug]]"`.

### Query

```bash
ccobsr search text "<query>"                              # full-text
ccobsr search jsonlogic '{"==":[{"var":"frontmatter.type"},"claim"]}'  # frontmatter
```

Always read `Research/<topic>/index.md` and `README.md` first to orient. Answer with `[[wikilinks]]` so the human can verify. If the answer required new reasoning, file it back via `ccobsr put Research/<topic>/outputs/reports/YYYY-MM-DD-<name>.md ...`.

### Synthesize / render outputs

- Reports: `Research/<topic>/outputs/reports/YYYY-MM-DD-<name>.md` — must cite `[[claim-*]]` pages, not raw sources.
- Slide decks: `Research/<topic>/outputs/slides/YYYY-MM-DD-<name>.md` — Marp format (rendered by the Obsidian Marp plugin).
- Figures: `Research/<topic>/outputs/figures/*.png` — `ccobsr put ... --content-type image/png` with the generating script stored alongside.

### Lint / health check

Periodically (LLM-run). Write findings to `outputs/reports/lint-YYYY-MM-DD.md`:

- Orphan pages (no backlinks).
- Claims without sources, or with `verifiability < 2` still marked `confirmed`.
- Contradictions (a claim's `contradicts:` target is also `confirmed`).
- Files in `_raw/` with no corresponding `sources/` (uncompiled backlog).
- Missing-data imputation candidates (gaps to fill via web search).
- New article candidates (interesting unpaged connections).
- New follow-up questions (append to `questions/`).

### Log

```bash
ccobsr log <topic-slug> "<message>"
```

Appends a JST-stamped entry to `Research/<topic-slug>/log.md`. Use liberally — every ingest, compile, query, lint, or synthesize pass should leave a trail.

## Common query patterns (JsonLogic)

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

## When NOT to use this skill

- The user wants you to edit arbitrary notes in their vault unrelated to research.
- The user wants an ad-hoc Q&A over a single document without filing anything.
- The user is working on code, not knowledge. Use other tools.
