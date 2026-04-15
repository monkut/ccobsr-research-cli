from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ccobsr.cli import _build_parser
from ccobsr.definitions import (
    DEFAULT_CONTENT_TYPE,
    EXTENSION_CONTENT_TYPES,
    TOPIC_SUBDIRS,
    CaptureKind,
)
from ccobsr.functions import (
    ApiResponse,
    _build_url,
    guess_content_type,
    now_jst_iso,
    sha256_file,
    topic_path,
)


class TestGuessContentType:
    def test_known_extensions(self, tmp_path: Path):
        assert guess_content_type("paper.pdf") == "application/pdf"
        assert guess_content_type("fig.png") == "image/png"
        assert guess_content_type("doc.md") == "text/markdown"
        assert guess_content_type("data.csv") == "text/csv"
        assert guess_content_type(tmp_path / "x.jpg") == "image/jpeg"

    def test_case_insensitive(self):
        assert guess_content_type("PAPER.PDF") == "application/pdf"

    def test_unknown_extension(self):
        assert guess_content_type("weird.xyz") == DEFAULT_CONTENT_TYPE

    def test_no_extension(self):
        assert guess_content_type("README") == DEFAULT_CONTENT_TYPE


class TestExtensionMap:
    def test_has_expected_keys(self):
        assert ".pdf" in EXTENSION_CONTENT_TYPES
        assert ".png" in EXTENSION_CONTENT_TYPES
        assert ".md" in EXTENSION_CONTENT_TYPES

    def test_values_are_strings(self):
        for ext, mime in EXTENSION_CONTENT_TYPES.items():
            assert ext.startswith(".")
            assert "/" in mime


class TestTopicPath:
    def test_research_prefix(self):
        assert topic_path("llm-agent-memory") == "Research/llm-agent-memory"

    def test_nested_slug(self):
        assert topic_path("foo-bar").startswith("Research/")


class TestTopicSubdirs:
    def test_contains_raw_subfolders(self):
        assert "_raw/papers" in TOPIC_SUBDIRS
        assert "_raw/images" in TOPIC_SUBDIRS
        assert "_raw/articles" in TOPIC_SUBDIRS

    def test_contains_wiki_folders(self):
        assert "sources" in TOPIC_SUBDIRS
        assert "claims" in TOPIC_SUBDIRS
        assert "concepts" in TOPIC_SUBDIRS
        assert "synthesis" in TOPIC_SUBDIRS
        assert "_meta" in TOPIC_SUBDIRS

    def test_contains_outputs_folders(self):
        assert "outputs/reports" in TOPIC_SUBDIRS
        assert "outputs/slides" in TOPIC_SUBDIRS
        assert "outputs/figures" in TOPIC_SUBDIRS


class TestCaptureKind:
    def test_all_kinds_are_lowercase(self):
        for kind in CaptureKind:
            assert kind.value.islower()

    def test_kinds_match_raw_subdirs(self):
        # Every CaptureKind must have a matching _raw/<kind>/ subdir.
        for kind in CaptureKind:
            assert f"_raw/{kind.value}" in TOPIC_SUBDIRS


class TestBuildUrl:
    def test_simple_path(self):
        with patch("ccobsr.functions.OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"):
            assert _build_url("vault/foo.md") == "https://127.0.0.1:27124/vault/foo.md"

    def test_nested_path(self):
        with patch("ccobsr.functions.OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"):
            url = _build_url("vault/Research/topic/sources/foo.md")
            assert url == "https://127.0.0.1:27124/vault/Research/topic/sources/foo.md"

    def test_spaces_are_encoded(self):
        with patch("ccobsr.functions.OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"):
            url = _build_url("vault/with space.md")
            assert "with%20space.md" in url

    def test_leading_slash_stripped(self):
        with patch("ccobsr.functions.OBSIDIAN_BASE_URL", "https://127.0.0.1:27124"):
            assert _build_url("/vault/foo.md") == "https://127.0.0.1:27124/vault/foo.md"


class TestSha256File:
    def test_deterministic(self, tmp_path: Path):
        f = tmp_path / "a.txt"
        f.write_bytes(b"hello world")
        digest = sha256_file(f)
        assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

    def test_different_content_different_hash(self, tmp_path: Path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(b"one")
        b.write_bytes(b"two")
        assert sha256_file(a) != sha256_file(b)


class TestNowJstIso:
    def test_has_tz_suffix(self):
        stamp = now_jst_iso()
        # +0900 is JST
        assert stamp.endswith("+0900")

    def test_parses_as_iso(self):
        stamp = now_jst_iso()
        # strptime with %z parses +0900 fine
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z")


class TestApiResponse:
    def test_text_decoding(self):
        r = ApiResponse(status=200, headers={}, body=b"hello")
        assert r.text() == "hello"

    def test_json_decoding(self):
        r = ApiResponse(status=200, headers={}, body=b'{"a": 1}')
        assert r.json() == {"a": 1}


class TestCliParserSmokeTest:
    def test_version_flag(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_parser_builds(self):
        parser = _build_parser()
        assert parser.prog == "ccobsr"

    def test_bootstrap_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["bootstrap", "my-topic"])
        assert args.command == "bootstrap"
        assert args.topic == "my-topic"

    def test_capture_subcommand(self, tmp_path: Path):
        f = tmp_path / "paper.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        parser = _build_parser()
        args = parser.parse_args(["capture", "my-topic", str(f), "--kind", "papers"])
        assert args.command == "capture"
        assert args.kind == "papers"
        assert args.topic == "my-topic"
