import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_LEVEL = "INFO"
LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()

# Obsidian Local REST API — HTTPS with self-signed cert on localhost by default.
DEFAULT_OBSIDIAN_BASE_URL = "https://127.0.0.1:27124"
OBSIDIAN_BASE_URL: str = os.getenv("OBSIDIAN_API_URL", DEFAULT_OBSIDIAN_BASE_URL)
OBSIDIAN_API_KEY: str | None = os.getenv("OBSIDIAN_API_KEY")

# The Local REST API uses a self-signed cert. Default to skipping verification
# since it's localhost-only. Override with CCOBSR_VERIFY_SSL=true.
VERIFY_SSL: bool = os.getenv("CCOBSR_VERIFY_SSL", "false").lower() == "true"

# Request timeout in seconds for REST calls.
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("CCOBSR_REQUEST_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT_SECONDS)))

# Vault prefix for research topics (matches RESEARCH_TOPIC_PROPOSAL.md §2).
RESEARCH_ROOT: str = os.getenv("CCOBSR_RESEARCH_ROOT", "Research")

# Local config/state directory.
CCOBSR_HOME: Path = Path(os.getenv("CCOBSR_HOME") or str(Path.home() / ".ccobsr")).expanduser().resolve()
LOG_DIR: Path = CCOBSR_HOME / "logs"

LOG_FORMAT = "%(asctime)s [%(levelname)s] (%(name)s) %(funcName)s: %(message)s"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3


def configure_logging() -> None:
    """Configure logging for the application. Call explicitly from entry points."""
    log_level = getattr(logging, LOG_LEVEL, logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(log_level)
    stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(stderr_handler)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_DIR / "ccobsr.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
