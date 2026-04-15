from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .definitions import CaptureKind
from .functions import (
    bootstrap_topic,
    capture_file,
    guess_content_type,
    install_skills,
    log_entry,
    search_jsonlogic,
    search_simple,
    vault_append,
    vault_delete,
    vault_get,
    vault_list,
    vault_put,
)
from .settings import configure_logging

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ccobsr",
        description="Claude Code Obsidian Research CLI — binary-safe client for the Obsidian Local REST API.",
    )
    parser.add_argument("--version", action="version", version=f"ccobsr {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # install
    p_install = sub.add_parser("install", help="Install bundled skills to ~/.claude/skills.")
    p_install.add_argument("--directory", type=Path, default=None, help="Override target skills directory.")

    # ls
    p_ls = sub.add_parser("ls", help="List a vault folder.")
    p_ls.add_argument("path", nargs="?", default="", help="Vault-relative folder path (empty = root).")

    # get
    p_get = sub.add_parser("get", help="Download a file from the vault.")
    p_get.add_argument("path", help="Vault-relative file path.")
    p_get.add_argument("-o", "--output", type=Path, default=None, help="Write bytes to this file instead of stdout.")
    p_get.add_argument(
        "--note-json",
        action="store_true",
        help="Request parsed note JSON (frontmatter, tags, stat).",
    )

    # put
    p_put = sub.add_parser("put", help="Upload a file (or literal content) to a vault path.")
    p_put.add_argument("path", help="Vault-relative destination path.")
    src_group = p_put.add_mutually_exclusive_group(required=True)
    src_group.add_argument("-f", "--file", type=Path, help="Local file to upload.")
    src_group.add_argument("-c", "--content", type=str, help="Literal string content to upload.")
    p_put.add_argument(
        "--content-type",
        default=None,
        help="MIME type (defaults: guessed from file extension, or text/markdown for --content).",
    )

    # append
    p_append = sub.add_parser("append", help="Append markdown content to a vault file.")
    p_append.add_argument("path", help="Vault-relative file path.")
    src_group_a = p_append.add_mutually_exclusive_group(required=True)
    src_group_a.add_argument("-c", "--content", type=str, help="Literal string content to append.")
    src_group_a.add_argument("-f", "--file", type=Path, help="Local file whose text content to append.")

    # delete
    p_delete = sub.add_parser("delete", help="Delete a vault file.")
    p_delete.add_argument("path", help="Vault-relative file path.")

    # search
    p_search = sub.add_parser("search", help="Search the vault.")
    search_sub = p_search.add_subparsers(dest="search_kind", required=True)

    p_search_text = search_sub.add_parser("text", help="Full-text search via /search/simple/.")
    p_search_text.add_argument("query", help="Search query string.")

    p_search_jl = search_sub.add_parser("jsonlogic", help="Frontmatter search via /search/ (JsonLogic).")
    p_search_jl.add_argument("expression", help="JsonLogic expression as JSON string.")

    # bootstrap
    p_bootstrap = sub.add_parser(
        "bootstrap",
        help="Create a new research topic under Research/<slug>/ with the full folder skeleton.",
    )
    p_bootstrap.add_argument("topic", help="Topic slug (kebab-case, e.g. 'llm-agent-memory').")

    # capture
    p_capture = sub.add_parser(
        "capture",
        help="Upload a source file into a topic's _raw/ folder and update the manifest.",
    )
    p_capture.add_argument("topic", help="Topic slug.")
    p_capture.add_argument("file", type=Path, help="Local file to capture.")
    p_capture.add_argument(
        "--kind",
        choices=[k.value for k in CaptureKind],
        required=True,
        help="Capture subfolder.",
    )
    p_capture.add_argument("--slug", default=None, help="Override the stored filename stem.")

    # log
    p_log = sub.add_parser("log", help="Append a JST-stamped entry to a topic's log.md.")
    p_log.add_argument("topic", help="Topic slug.")
    p_log.add_argument("message", help="Log message.")

    return parser


def _handle_install(args: argparse.Namespace) -> int:
    installed = install_skills(directory=args.directory)
    if installed:
        print("Installed skills:")  # noqa: T201
        for name in installed:
            print(f"  - {name}")  # noqa: T201
    else:
        print("No skills installed (target directory missing).", file=sys.stderr)  # noqa: T201
    return 0


def _handle_ls(args: argparse.Namespace) -> int:
    for entry in vault_list(args.path):
        print(entry)  # noqa: T201
    return 0


def _handle_get(args: argparse.Namespace) -> int:
    resp = vault_get(args.path, as_note_json=args.note_json)
    if args.output:
        args.output.write_bytes(resp.body)
        logger.info("Wrote %d bytes to %s", len(resp.body), args.output)
    else:
        sys.stdout.buffer.write(resp.body)
        if not resp.body.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
    return 0


def _handle_put(args: argparse.Namespace) -> int:
    if args.file:
        body = args.file.read_bytes()
        content_type = args.content_type or guess_content_type(args.file)
    else:
        body = args.content.encode("utf-8")
        content_type = args.content_type or "text/markdown"
    vault_put(args.path, body, content_type=content_type)
    logger.info("PUT %s (%d bytes, %s)", args.path, len(body), content_type)
    return 0


def _handle_append(args: argparse.Namespace) -> int:
    content = args.content or args.file.read_text()
    vault_append(args.path, content)
    logger.info("Appended to %s", args.path)
    return 0


def _handle_delete(args: argparse.Namespace) -> int:
    vault_delete(args.path)
    logger.info("Deleted %s", args.path)
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    if args.search_kind == "text":
        results = search_simple(args.query)
    else:
        results = search_jsonlogic(args.expression)
    print(json.dumps(results, indent=2))  # noqa: T201
    return 0


def _handle_bootstrap(args: argparse.Namespace) -> int:
    created = bootstrap_topic(args.topic)
    print(f"Bootstrapped topic '{args.topic}' with {len(created)} files.")  # noqa: T201
    return 0


def _handle_capture(args: argparse.Namespace) -> int:
    kind = CaptureKind(args.kind)
    vault_path, digest = capture_file(args.topic, args.file, kind, slug=args.slug)
    print(f"Captured {args.file} -> {vault_path}")  # noqa: T201
    print(f"sha256: {digest}")  # noqa: T201
    return 0


def _handle_log(args: argparse.Namespace) -> int:
    entry = log_entry(args.topic, args.message)
    print(entry.rstrip())  # noqa: T201
    return 0


HANDLERS = {
    "install": _handle_install,
    "ls": _handle_ls,
    "get": _handle_get,
    "put": _handle_put,
    "append": _handle_append,
    "delete": _handle_delete,
    "search": _handle_search,
    "bootstrap": _handle_bootstrap,
    "capture": _handle_capture,
    "log": _handle_log,
}


def main() -> None:
    configure_logging()
    parser = _build_parser()
    args = parser.parse_args()

    handler = HANDLERS[args.command]
    try:
        rc = handler(args)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Command '%s' failed", args.command)
        print(f"error: {exc}", file=sys.stderr)  # noqa: T201
        sys.exit(1)
    sys.exit(rc)


if __name__ == "__main__":
    main()
