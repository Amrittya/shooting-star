"""Structured logging setup.

We use `structlog` with two output modes:

- `json`: single-line JSON per record. Default for paper/live; ships cleanly
  to CloudWatch/Loki without further parsing.
- `console`: colorized human-readable output. Default for local dev.

**Secret redaction:** any field whose key matches a `SECRET_KEY_PATTERN` is
replaced with `"<redacted>"` before serialization. `SecretStr` values from
pydantic are auto-redacted by structlog's normalization step.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import TYPE_CHECKING, Any

import structlog
from pydantic import SecretStr

from ti_core.config import LogFormat, Settings

if TYPE_CHECKING:
    from pathlib import Path

# Case-insensitive pattern of field names that must never appear in logs.
SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|api[_-]?secret|access[_-]?token|password|passwd|"
    r"secret|token|authorization|auth[_-]?token|private[_-]?key|"
    r"kite[_-]?api|anthropic[_-]?api|openai[_-]?api)"
)


def _redact_secrets(
    _logger: Any,
    _name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Redact any key that looks like a secret and any SecretStr value."""
    for key in list(event_dict):
        value = event_dict[key]
        if isinstance(value, SecretStr):
            event_dict[key] = "<redacted:SecretStr>"
        elif SECRET_KEY_PATTERN.search(key):
            event_dict[key] = "<redacted>"
        elif isinstance(value, Mapping):
            # Shallow recurse — depth 1 is enough for our nested contexts
            event_dict[key] = _redact_mapping(value)
    return event_dict


def _redact_mapping(m: Mapping[str, Any]) -> dict[str, Any]:
    """Redact secret keys/values inside a nested mapping."""
    out: dict[str, Any] = {}
    for k, v in m.items():
        if isinstance(v, SecretStr):
            out[k] = "<redacted:SecretStr>"
        elif SECRET_KEY_PATTERN.search(k):
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def configure_logging(settings: Settings) -> None:
    """Configure the global structlog + stdlib logging.

    Idempotent — safe to call multiple times.
    """
    # ---- stdlib logging: minimal, structlog handles the rest ----
    log_level = getattr(logging, settings.log_level)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.log_file:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=handlers,
        force=True,
    )

    # ---- structlog processors ----
    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        _redact_secrets,  # ALWAYS before the renderer
    ]

    if settings.log_format is LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer(sort_keys=True))
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound logger. Prefer `get_logger(__name__)`."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger


def audit_log_path(base_dir: Path, subject: str) -> Path:
    """Return the canonical path for an audit log of `subject`.

    Audit logs are never rotated — they are the source of truth for
    reconstruction of what the system did. Every LLM call, every order
    submission, every risk-engine decision gets an audit entry.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{subject}.jsonl"
