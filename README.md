# ccobsr — Claude Code Obsidian Research CLI

A binary-safe Python client for the [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api), shaped for building and maintaining Karpathy-style LLM research wikis inside an Obsidian vault.

Ships with a bundled Claude Code skill (`ccobsr-research`) that teaches Claude how to bootstrap research topics, capture sources, compile a wiki, query it, and file outputs back in — all via this CLI, with the Obsidian vault as the single source of truth.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/guides/install-python/)
- Obsidian with the **Local REST API** community plugin enabled
- [Claude Code CLI](https://claude.ai) (`claude`) — for the bundled skill

## Installation

```bash
uv tool install . --python 3.14
```

Or from GitHub:

```bash
uv tool install "ccobsr @ git+https://github.com/monkut/ccobsr-research-cli" --python 3.14
```

Or run directly with `uvx`:

```bash
uvx --from . --python 3.14 ccobsr --help
```

## Obsidian Local REST API setup

`ccobsr` talks to Obsidian through the community plugin [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) by Adam Coddington. The plugin runs inside Obsidian and exposes the vault over HTTP(S) on `localhost`. Obsidian must be **open** with your target vault loaded for `ccobsr` to reach it.

### 1. Install and enable the plugin

1. Open Obsidian → **Settings** → **Community plugins**.
2. If Restricted mode is on, click **Turn off restricted mode** (community plugins are opt-in).
3. Click **Browse**, search for **`Local REST API`**, select the plugin by _Adam Coddington_, and click **Install**.
4. After install, click **Enable** (or toggle it on in the installed plugins list).

### 2. Grab the API key

1. Still in **Settings**, scroll the left sidebar down to **Community plugins** → **Local REST API** (plugin options).
2. Copy the **API Key** shown at the top of the plugin settings panel. Treat this like a password — anything with the key can read and write your vault.
3. Note the HTTPS and HTTP port numbers. Defaults are:
   - **HTTPS**: `https://127.0.0.1:27124` (self-signed cert, recommended)
   - **HTTP**:  `http://127.0.0.1:27123` (off by default; enable only if you need it for a specific client)

### 3. About the self-signed certificate

The plugin generates a self-signed TLS cert on first run so traffic between `ccobsr` and Obsidian is encrypted even on `localhost`. Because the cert isn't signed by a public CA, most clients (curl, Python, browsers) refuse it by default.

`ccobsr` **defaults to not verifying** the cert (`CCOBSR_VERIFY_SSL=false`) since the endpoint is bound to `127.0.0.1`. If you want strict verification:

1. In the plugin settings, click **Download certificate** and save the `.crt` file.
2. Trust it at the OS level (e.g. `sudo trust anchor obsidian-local-rest-api.crt` on Fedora, or add it to your system keychain on macOS).
3. Export `CCOBSR_VERIFY_SSL=true`.

### 4. Export the environment variables

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export OBSIDIAN_API_URL="https://127.0.0.1:27124"
export OBSIDIAN_API_KEY="<paste the API key from the plugin settings>"
```

Reload your shell (`exec $SHELL`) or `source` the profile.

### 5. Verify the connection

With Obsidian running and your vault open:

```bash
ccobsr ls
```

You should see the top-level folders of your vault listed, one per line. If you get `Could not reach Obsidian Local REST API...`, Obsidian is not running or the plugin is disabled. If you get `HTTP 401`, your `OBSIDIAN_API_KEY` is wrong or not exported into the current shell.

## Configuration

Set these environment variables (e.g. in your shell profile):

```bash
export OBSIDIAN_API_URL="https://127.0.0.1:27124"    # default
export OBSIDIAN_API_KEY="<key from the Obsidian Local REST API plugin settings>"
```

Optional:

| Variable | Default | Description |
|---|---|---|
| `CCOBSR_VERIFY_SSL` | `false` | Verify the self-signed cert on the local API. Default off. |
| `CCOBSR_REQUEST_TIMEOUT` | `30` | Request timeout in seconds. |
| `CCOBSR_RESEARCH_ROOT` | `Research` | Vault folder prefix for research topics. |
| `CCOBSR_HOME` | `~/.ccobsr` | Local config/log directory. |
| `LOG_LEVEL` | `INFO` | Logging verbosity. |

## Usage

```
ccobsr <command> [options]
```

### Commands

| Command | Description |
|---|---|
| `bootstrap <topic>` | Create `Research/<topic>/` with the full folder skeleton + seeded README, index, log, manifest, taxonomy |
| `capture <topic> <file> --kind {articles,papers,images,datasets,transcripts,repos,clips}` | Upload a source file into `_raw/` and append a row to `manifest.md` |
| `log <topic> "<message>"` | Append a JST-stamped entry to `log.md` |
| `ls [path]` | List a vault folder |
| `get <path> [-o FILE] [--note-json]` | Download a file (binary-safe) |
| `put <path> --file FILE` / `--content TEXT` | Upload bytes or literal content |
| `append <path> --content TEXT` / `--file FILE` | Append markdown content to a file |
| `delete <path>` | Delete a vault file |
| `search text <query>` | Full-text search |
| `search jsonlogic '<expr>'` | Frontmatter search via JsonLogic |
| `install [--directory DIR]` | Install bundled skills to `~/.claude/skills` |

### Research workflow

Canonical Karpathy-style loop. See the bundled skill at `ccobsr/skills/ccobsr-research/SKILL.md` for the full method.

```bash
# 1. Bootstrap a topic
ccobsr bootstrap llm-agent-memory

# 2. Capture a primary source
ccobsr capture llm-agent-memory ~/Downloads/mem-gpt.pdf --kind papers --slug packer-2023-memgpt

# 3. (LLM) read the file, compile a sources/ page + claims/ pages
ccobsr get "Research/llm-agent-memory/_raw/papers/packer-2023-memgpt.pdf" -o /tmp/mem.pdf
ccobsr put "Research/llm-agent-memory/sources/packer-2023-memgpt.md" --content "---
type: source
...
---
## Summary
..."

# 4. Log it
ccobsr log llm-agent-memory "compiled [[sources/packer-2023-memgpt]]: +3 claims, +1 concept"

# 5. Query later
ccobsr search jsonlogic '{"and":[
  {"==":[{"var":"frontmatter.type"},"claim"]},
  {">=":[{"var":"frontmatter.verifiability"},3]}
]}'
```

### Binary uploads

PDFs, images, and datasets all work — the Obsidian Local REST API accepts `*/*` on `PUT`, and `ccobsr` guesses the Content-Type from the file extension. Round-trip byte-identity is verified by the tests.

```bash
ccobsr put "Research/topic/_raw/images/diagram.png" --file ./diagram.png
ccobsr get "Research/topic/_raw/images/diagram.png" -o /tmp/roundtrip.png
```

## Bundled skill: `ccobsr-research`

```bash
ccobsr install
```

Copies the skill to `~/.claude/skills/ccobsr-research/`, where Claude Code auto-discovers it. The skill encodes:

- **Evidence-first methodology** — primary sources preferred, `verifiability` and `popularity` required on every source/claim
- **WORM `_raw/` rule** — never re-write a captured source
- **Evidence precedes synthesis** — `sources/` must exist before `claims/`; `claims/` must exist before `synthesis/`
- **JST timestamps** everywhere
- **Single source of truth** — the Obsidian vault; no filesystem sidecar

## Project Structure

```
ccobsr/
    __init__.py              # Package version
    cli.py                   # argparse entry point and handlers
    definitions.py           # MIME map, CaptureKind enum, bootstrap templates
    functions.py             # REST API client + research workflow helpers
    settings.py              # env vars and logging
    skills/
        ccobsr-research/
            SKILL.md         # the bundled skill definition
tests/
    test_ccobsr.py           # unit tests (url build, hash, guessing)
pyproject.toml
LICENSE
README.md
```

## Development

```bash
pre-commit install
uv sync
uv run poe check        # ruff
uv run poe typecheck    # pyright
uv run poe test         # pytest
```

## Related

- [askcc-cli](https://github.com/monkut/askcc-cli) — sibling one-shot Claude Code CLI executor; `ccobsr` borrows its packaging and skill-install layout.
- [Obsidian Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) — the upstream plugin.
- [Karpathy's "LLM Knowledge Bases"](https://x.com/karpathy/status/2039805659525644595) — the pattern this tool implements.
