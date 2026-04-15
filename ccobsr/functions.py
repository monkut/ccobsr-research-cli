from __future__ import annotations

import hashlib
import json
import logging
import shutil
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.resources import files as package_files
from pathlib import Path
from zoneinfo import ZoneInfo

from .definitions import (
    DEFAULT_CONTENT_TYPE,
    EXTENSION_CONTENT_TYPES,
    INDEX_TEMPLATE,
    LOG_TEMPLATE,
    MANIFEST_TEMPLATE,
    README_TEMPLATE,
    TAXONOMY_TEMPLATE,
    TOPIC_SUBDIRS,
    CaptureKind,
)
from .settings import (
    OBSIDIAN_API_KEY,
    OBSIDIAN_BASE_URL,
    REQUEST_TIMEOUT_SECONDS,
    RESEARCH_ROOT,
    VERIFY_SSL,
)

logger = logging.getLogger(__name__)

CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_SKILLS_DIR = CLAUDE_HOME / "skills"

JST = ZoneInfo("Asia/Tokyo")

HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404


class ObsidianAPIError(RuntimeError):
    """Raised when the Obsidian Local REST API returns an error status."""

    def __init__(self, status: int, message: str, body: bytes = b"") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


@dataclass(frozen=True)
class ApiResponse:
    status: int
    headers: dict[str, str]
    body: bytes

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> object:
        return json.loads(self.body.decode("utf-8"))


def _require_api_key() -> str:
    if not OBSIDIAN_API_KEY:
        msg = (
            "OBSIDIAN_API_KEY is not set. Set it in the environment or via your shell profile. "
            "Get the key from Obsidian Settings → Community plugins → Local REST API."
        )
        raise RuntimeError(msg)
    return OBSIDIAN_API_KEY


def _ssl_context() -> ssl.SSLContext | None:
    """Return an SSL context appropriate for the configured base URL."""
    if not OBSIDIAN_BASE_URL.startswith("https://"):
        return None
    if VERIFY_SSL:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_url(path: str) -> str:
    """Join the base URL with a path, URL-encoding each segment while preserving '/'."""
    stripped = path.lstrip("/")
    segments = [urllib.parse.quote(seg, safe="") for seg in stripped.split("/")]
    return f"{OBSIDIAN_BASE_URL.rstrip('/')}/{'/'.join(segments)}"


def _request(
    method: str,
    path: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> ApiResponse:
    """Low-level HTTP call to the Obsidian Local REST API."""
    url = _build_url(path)
    final_headers = {"Authorization": f"Bearer {_require_api_key()}"}
    if headers:
        final_headers.update(headers)

    req = urllib.request.Request(url, data=body, method=method, headers=final_headers)  # noqa: S310
    logger.debug("%s %s", method, url)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS, context=_ssl_context()) as resp:  # noqa: S310
            return ApiResponse(
                status=resp.status,
                headers=dict(resp.headers.items()),
                body=resp.read(),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        logger.exception("%s %s -> HTTP %d: %s", method, url, exc.code, body[:500].decode("utf-8", errors="replace"))
        raise ObsidianAPIError(exc.code, exc.reason, body) from exc
    except urllib.error.URLError as exc:
        msg = f"Could not reach Obsidian Local REST API at {OBSIDIAN_BASE_URL}: {exc.reason}"
        raise RuntimeError(msg) from exc


def guess_content_type(path: Path | str) -> str:
    """Guess a Content-Type from a file extension."""
    suffix = Path(path).suffix.lower()
    return EXTENSION_CONTENT_TYPES.get(suffix, DEFAULT_CONTENT_TYPE)


def vault_list(vault_path: str) -> list[str]:
    """List files in a vault folder. Pass '' for the root."""
    normalized = vault_path.strip("/")
    api_path = f"vault/{normalized}/" if normalized else "vault/"
    resp = _request("GET", api_path, headers={"Accept": "application/json"})
    data = resp.json()
    if not isinstance(data, dict) or "files" not in data:
        msg = f"Unexpected list response shape: {data!r}"
        raise TypeError(msg)
    return list(data["files"])


def vault_get(vault_path: str, *, as_note_json: bool = False) -> ApiResponse:
    """GET a file from the vault. Set as_note_json=True for parsed frontmatter + tags."""
    normalized = vault_path.strip("/")
    accept = "application/vnd.olrapi.note+json" if as_note_json else "*/*"
    return _request("GET", f"vault/{normalized}", headers={"Accept": accept})


def vault_put(vault_path: str, body: bytes, *, content_type: str) -> ApiResponse:
    """PUT bytes to a vault path. Parent directories are created implicitly."""
    normalized = vault_path.strip("/")
    return _request("PUT", f"vault/{normalized}", body=body, headers={"Content-Type": content_type})


def vault_append(vault_path: str, content: str) -> ApiResponse:
    """Append markdown content to a vault file. Creates the file if missing."""
    normalized = vault_path.strip("/")
    return _request(
        "POST",
        f"vault/{normalized}",
        body=content.encode("utf-8"),
        headers={"Content-Type": "text/markdown"},
    )


def vault_delete(vault_path: str) -> ApiResponse:
    normalized = vault_path.strip("/")
    return _request("DELETE", f"vault/{normalized}")


def search_simple(query: str) -> list[dict]:
    """Full-text search across the vault."""
    encoded = urllib.parse.quote(query, safe="")
    resp = _request("POST", f"search/simple/?query={encoded}")
    data = resp.json()
    if not isinstance(data, list):
        msg = f"Unexpected search/simple response shape: {data!r}"
        raise TypeError(msg)
    return data


def search_jsonlogic(expression: str) -> list[dict]:
    """Frontmatter search via JsonLogic. `expression` is a JSON string."""
    resp = _request(
        "POST",
        "search/",
        body=expression.encode("utf-8"),
        headers={"Content-Type": "application/vnd.olrapi.jsonlogic+json"},
    )
    data = resp.json()
    if not isinstance(data, list):
        msg = f"Unexpected search/ response shape: {data!r}"
        raise TypeError(msg)
    return data


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def now_jst_iso() -> str:
    """Return current time as an ISO-8601 string in JST."""
    return datetime.now(tz=UTC).astimezone(JST).strftime("%Y-%m-%dT%H:%M:%S%z")


def topic_path(topic_slug: str) -> str:
    """Return the vault-relative root for a research topic."""
    return f"{RESEARCH_ROOT}/{topic_slug}"


def bootstrap_topic(topic_slug: str) -> list[str]:
    """Create the per-topic folder skeleton. Returns the list of created paths."""
    root = topic_path(topic_slug)
    created = now_jst_iso()
    substitutions = {"topic": topic_slug, "created": created}
    created_paths: list[str] = []

    seed_files: tuple[tuple[str, str], ...] = (
        (f"{root}/README.md", README_TEMPLATE.format(**substitutions)),
        (f"{root}/index.md", INDEX_TEMPLATE.format(**substitutions)),
        (f"{root}/log.md", LOG_TEMPLATE.format(**substitutions)),
        (f"{root}/_meta/manifest.md", MANIFEST_TEMPLATE.format(**substitutions)),
        (f"{root}/_meta/taxonomy.md", TAXONOMY_TEMPLATE.format(**substitutions)),
    )
    for path, content in seed_files:
        vault_put(path, content.encode("utf-8"), content_type="text/markdown")
        created_paths.append(path)
        logger.info("Created %s", path)

    # Create an empty .gitkeep-style marker in each conventional subdir so the folder
    # shows up in the Obsidian tree immediately. These are tiny stub files, not WORM.
    for subdir in TOPIC_SUBDIRS:
        marker_path = f"{root}/{subdir}/.gitkeep"
        vault_put(marker_path, b"", content_type="text/plain")
        created_paths.append(marker_path)

    return created_paths


def capture_file(
    topic_slug: str,
    source_path: Path,
    kind: CaptureKind,
    *,
    slug: str | None = None,
) -> tuple[str, str]:
    """Upload a file into `<topic>/_raw/<kind>/` and append a row to manifest.md.

    Returns (vault_path, sha256).
    """
    if not source_path.exists():
        msg = f"Source file not found: {source_path}"
        raise FileNotFoundError(msg)

    digest = sha256_file(source_path)
    size = source_path.stat().st_size
    filename = f"{slug}{source_path.suffix}" if slug else source_path.name

    root = topic_path(topic_slug)
    vault_path = f"{root}/_raw/{kind.value}/{filename}"
    content_type = guess_content_type(source_path)

    body = source_path.read_bytes()
    vault_put(vault_path, body, content_type=content_type)
    logger.info("Captured %s -> %s (%s, %d bytes)", source_path, vault_path, content_type, size)

    captured_at = now_jst_iso()
    row = f"| [[{vault_path}]] | `{digest}` | {captured_at} | {kind.value} | {size} |\n"
    vault_append(f"{root}/_meta/manifest.md", row)

    log_entry = f"- {captured_at} — captured `{kind.value}` [[{vault_path}]] (`{digest[:12]}…`)\n"
    vault_append(f"{root}/log.md", log_entry)

    return vault_path, digest


def log_entry(topic_slug: str, message: str) -> str:
    """Append a timestamped log entry to a topic's log.md."""
    root = topic_path(topic_slug)
    stamped = f"- {now_jst_iso()} — {message}\n"
    vault_append(f"{root}/log.md", stamped)
    return stamped


def install_skills(directory: Path | None = None) -> list[str]:
    """Copy bundled skills to ~/.claude/skills (or an override directory)."""
    target_dir = directory.expanduser() if directory else CLAUDE_SKILLS_DIR
    if not target_dir.parent.is_dir():
        logger.warning("Skill target parent does not exist: %s. Skipping.", target_dir.parent)
        return []

    target_dir.mkdir(parents=True, exist_ok=True)
    skills_source = package_files("ccobsr") / "skills"
    installed: list[str] = []
    for skill_dir in sorted(skills_source.iterdir(), key=lambda p: p.name):
        if not skill_dir.is_dir() or skill_dir.name.startswith("__"):
            continue
        dest = target_dir / skill_dir.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(str(skill_dir), dest)
        logger.info("Installed skill '%s' to %s", skill_dir.name, dest)
        installed.append(skill_dir.name)
    return installed
