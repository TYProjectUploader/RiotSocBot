"""Central logging setup: console for watching live, rotating files for after the fact.

Nothing configured logging before this, so the `logger.exception(...)` calls already in
the cogs fell back to logging.lastResort on stderr - fine while you are watching the
console, useless once it has scrolled past.
"""
import logging
import logging.handlers
import os
from pathlib import Path

# Anchored to this file,
# systemd starts the bot from somewhere else.
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "data"

BOT_LOG = LOG_DIR / "bot.log"      # everything
ERROR_LOG = LOG_DIR / "errors.log" # ERROR and above only, for quick triage

MAX_BYTES = 2 * 1024 * 1024 #2mb siees
BACKUP_COUNT = 5

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _file_handler(path: Path, level: int, formatter: logging.Formatter) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
        delay=True,  # don't create the file until there is something to write
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging(level: int | None = None) -> None:
    """Attach console + rotating file handlers to the root logger.

    Call once at startup, before bot.run(..., log_handler=None). Everything the cogs
    and discord.py log propagates up to root, so the files capture the lot - including
    slash command errors and event handler tracebacks discord.py logs itself.

    Level defaults to INFO; override with LOG_LEVEL=DEBUG in .env when digging into
    something (DEBUG is chatty - discord.http logs every request).
    """
    if level is None:
        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_FORMAT, _DATE_FORMAT)

    root = logging.getLogger()
    root.setLevel(level)

    # Idempotent - re-running must not stack duplicate handlers.
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    root.addHandler(_file_handler(BOT_LOG, level, formatter))
    root.addHandler(_file_handler(ERROR_LOG, logging.ERROR, formatter))

    # Third-party noise that would otherwise bury the interesting lines.
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("praw").setLevel(logging.WARNING)
    logging.getLogger("prawcore").setLevel(logging.WARNING)
