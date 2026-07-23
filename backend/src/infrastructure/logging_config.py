"""Uygulama loglarini konsol ve donen dosya handler'lariyla yapilandirir."""

from __future__ import annotations

import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _env_int(name: str, default: int, minimum: int) -> int:
    """Pozitif sayisal env degerini guvenli varsayilanla okur."""
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


_QUERY_SECRET_RE = re.compile(
    r"([?&](?:token|stream_token|access_token|refresh_token|password|secret|key|authorization)=)([^&\s\"']+)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_RTSP_CREDENTIAL_RE = re.compile(r"(rtsp://)([^:@/\s]+):([^@/\s]+)@", re.IGNORECASE)


def mask_sensitive_log_text(value: str) -> str:
    """Log metnindeki token, query secret ve RTSP parolalarini maskeler."""
    masked = _RTSP_CREDENTIAL_RE.sub(r"\1\2:****@", value)
    masked = _QUERY_SECRET_RE.sub(r"\1****", masked)
    return _BEARER_RE.sub("Bearer ****", masked)


def _sanitize_value(value):
    """LogRecord args/extra icindeki string degerleri guvenli hale getirir."""
    if isinstance(value, str):
        return mask_sensitive_log_text(value)
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item) for key, item in value.items()}
    return value


class SensitiveLogFilter(logging.Filter):
    """Handler'a ulasan kayitlarda hassas metinleri maskeleyen filtre."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Kaydi engellemez; sadece mesaj ve argumanlari sanitize eder."""
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_log_text(record.msg)
        if record.args:
            record.args = _sanitize_value(record.args)
        return True


class JsonLogFormatter(logging.Formatter):
    """Log kayitlarini tek satir JSON nesnesi olarak bicimlendirir."""

    _reserved = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        """LogRecord alanlarini SIEM uyumlu JSON satirina cevirir."""
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._reserved and not key.startswith("_")
        }
        if extra:
            payload["extra"] = _sanitize_value(extra)
        return json.dumps(payload, ensure_ascii=False, default=str)


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

    log_format = os.environ.get("APP_LOG_FORMAT", "text").strip().lower()
    if log_format == "json":
        formatter = JsonLogFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z")
    else:
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
    file_handler.addFilter(SensitiveLogFilter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    console_handler.addFilter(SensitiveLogFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
