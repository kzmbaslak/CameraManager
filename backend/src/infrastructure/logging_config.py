"""Uygulama loglarini konsol ve donen dosya handler'lariyla yapilandirir."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _env_int(name: str, default: int, minimum: int) -> int:
    """Pozitif sayisal env degerini guvenli varsayilanla okur."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


def configure_application_logging() -> None:
    """Root logger'i konsol ve rotate edilen dosya ciktilariyla kurar."""
    backend_root = Path(__file__).resolve().parents[2]
    log_level_name = os.environ.get("APP_LOG_LEVEL", "INFO").strip().upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_dir = Path(
        os.environ.get(
            "APP_LOG_DIR",
            str(backend_root / "logs"),
        )
    )
    if not log_dir.is_absolute():
        log_dir = backend_root / log_dir
    max_bytes = _env_int("APP_LOG_MAX_BYTES", 10 * 1024 * 1024, 1024 * 1024)
    backup_count = _env_int("APP_LOG_BACKUP_COUNT", 5, 1)
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    file_handler = RotatingFileHandler(
        log_dir / "application.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
