"""Logging Service - Centralized file-based logging configuration.

Because ADTUI is a full-screen Textual TUI, stderr output (logging and
tracebacks) is normally not visible while the app is running. This service
configures a rotating log file under the config directory so errors and
uncaught crashes are persisted for later inspection.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

try:
    from .platform_service import PlatformService
except ImportError:
    from platform_service import PlatformService

# Rotation settings
_MAX_BYTES = 1_000_000  # ~1 MB per file
_BACKUP_COUNT = 3
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

# Guard to keep setup idempotent across multiple entry points.
_configured = False


def get_log_dir() -> Path:
    """Return the directory where log files are stored."""
    return PlatformService.get_config_dir() / "logs"


def get_log_file_path() -> Path:
    """Return the full path to the main log file."""
    return get_log_dir() / "adtui.log"


def setup_logging(level: int = logging.INFO) -> Optional[Path]:
    """Configure root logging with a rotating file handler and crash hook.

    - Root logger is set to DEBUG so handlers decide what passes.
    - A RotatingFileHandler captures ``level`` and above (default INFO).
    - A stderr StreamHandler captures WARNING and above (preserves the
      previous console behavior of suppressing info messages on quit).
    - ``sys.excepthook`` is installed so uncaught exceptions are written to
      the log file with a full traceback.

    Logging setup never crashes the app: if the log directory cannot be
    created or written, it falls back to console-only logging.

    Returns:
        The Path to the log file if file logging was enabled, else None.
    """
    global _configured
    if _configured:
        return get_log_file_path()

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(_LOG_FORMAT)

    # Console handler (stderr) - keep quiet, WARNING and above only.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    log_file: Optional[Path] = None
    try:
        log_dir = get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "adtui.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception as e:  # pragma: no cover - defensive fallback
        # Never let logging setup take down the app.
        log_file = None
        logging.getLogger(__name__).warning(
            "Could not set up file logging: %s", e
        )

    _install_excepthook()

    _configured = True
    return log_file


def _install_excepthook() -> None:
    """Route uncaught exceptions to the logging system."""
    previous_hook = sys.excepthook

    def _handle_exception(exc_type, exc_value, exc_traceback):
        # Let KeyboardInterrupt behave normally (clean Ctrl+C).
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc_value, exc_traceback)
            return

        logging.getLogger(__name__).critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        previous_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _handle_exception
