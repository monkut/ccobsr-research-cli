from enum import StrEnum

# MIME type guesses for common capture kinds. The Obsidian REST API accepts */*
# on PUT, so the Content-Type is only used to be explicit on the wire.
EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".html": "text/html",
    ".xml": "application/xml",
    ".zip": "application/zip",
}

DEFAULT_CONTENT_TYPE = "application/octet-stream"


class CaptureKind(StrEnum):
    ARTICLES = "articles"
    PAPERS = "papers"
    IMAGES = "images"
    DATASETS = "datasets"
    TRANSCRIPTS = "transcripts"
    REPOS = "repos"
    CLIPS = "clips"


# Research topic subdirectories created by `ccobsr bootstrap`.
# Matches RESEARCH_TOPIC_PROPOSAL.md §2.
TOPIC_SUBDIRS: tuple[str, ...] = (
    "_raw/articles",
    "_raw/papers",
    "_raw/images",
    "_raw/datasets",
    "_raw/transcripts",
    "_raw/repos",
    "_raw/clips",
    "sources",
    "claims",
    "concepts",
    "entities",
    "comparisons",
    "questions",
    "synthesis",
    "outputs/reports",
    "outputs/slides",
    "outputs/figures",
    "_meta",
)

# Bootstrap file templates. `{topic}` is substituted at bootstrap time.
README_TEMPLATE = """\
---
type: research-topic
topic: {topic}
created: {created}
---

# {topic}

## Scope

<TODO: one-paragraph scope statement for this research topic>

## Key Questions

<TODO: the driving questions — also filed individually under questions/>

## Non-goals

<TODO: what this research explicitly does not cover>

## Success Criteria

<TODO: what "done" looks like>
"""

INDEX_TEMPLATE = """\
---
type: index
topic: {topic}
updated: {created}
---

# {topic} — Index

> Auto-maintained by the LLM compile step. Do not hand-edit.

## Concepts

## Entities

## Sources

## Claims

## Synthesis
"""

LOG_TEMPLATE = """\
---
type: log
topic: {topic}
---

# {topic} — Log

- {created} — bootstrapped via `ccobsr bootstrap {topic}`
"""

MANIFEST_TEMPLATE = """\
---
type: manifest
topic: {topic}
---

# {topic} — Capture Manifest

Append-only record of every file captured into `_raw/`. One row per capture.

| path | sha256 | captured (JST) | source_kind | size |
|------|--------|----------------|-------------|------|
"""

TAXONOMY_TEMPLATE = """\
---
type: taxonomy
topic: {topic}
---

# {topic} — Taxonomy

Controlled tag vocabulary for this topic. Extend as needed.

## topic/

- topic/{topic}

## kind/

- kind/paper
- kind/article
- kind/transcript
- kind/dataset
- kind/repo

## status/

- status/open
- status/confirmed
- status/refuted
- status/superseded
"""
