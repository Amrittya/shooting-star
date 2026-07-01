"""Tests for `ti_core.logging`.

Focus on the redaction contract — logs must never leak secrets.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import pytest
import structlog
from pydantic import SecretStr
from ti_core.config import LogFormat, Settings, reset_settings_for_testing
from ti_core.logging import (
    SECRET_KEY_PATTERN,
    _redact_mapping,
    _redact_secrets,
    audit_log_path,
    configure_logging,
    get_logger,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_settings_for_testing()


class TestRedactionPattern:
    @pytest.mark.parametrize(
        "key",
        [
            "api_key",
            "api-key",
            "API_KEY",
            "kite_api_key",
            "anthropic_api_key",
            "access_token",
            "access-token",
            "password",
            "passwd",
            "secret",
            "authorization",
            "auth_token",
            "private_key",
        ],
    )
    def test_matches_secret_keys(self, key: str) -> None:
        assert SECRET_KEY_PATTERN.search(key) is not None

    @pytest.mark.parametrize(
        "key",
        [
            "symbol",
            "quantity",
            "order_id",
            "strategy_name",
            "regime",
        ],
    )
    def test_does_not_match_ordinary_keys(self, key: str) -> None:
        assert SECRET_KEY_PATTERN.search(key) is None


class TestRedactionProcessor:
    def test_redacts_secret_key(self) -> None:
        event: dict[str, Any] = {"api_key": "hunter2", "event": "kite_login"}
        out = _redact_secrets(None, "info", event)
        assert out["api_key"] == "<redacted>"
        assert out["event"] == "kite_login"

    def test_redacts_secretstr_value(self) -> None:
        event: dict[str, Any] = {"token": SecretStr("abc"), "event": "test"}
        out = _redact_secrets(None, "info", event)
        assert out["token"] == "<redacted:SecretStr>"  # noqa: S105 — literal is the redaction marker, not a password

    def test_redacts_nested_secret(self) -> None:
        event: dict[str, Any] = {
            "context": {"kite_api_key": "leak-me", "instrument": "NIFTY"},
        }
        out = _redact_secrets(None, "info", event)
        nested: dict[str, Any] = out["context"]
        assert nested["kite_api_key"] == "<redacted>"
        assert nested["instrument"] == "NIFTY"

    def test_redact_mapping_helper(self) -> None:
        out = _redact_mapping({"password": "x", "symbol": "y"})
        assert out == {"password": "<redacted>", "symbol": "y"}


class TestConfigureLogging:
    def _capture_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> list[dict[str, Any]]:
        """Configure logging and capture emitted JSON lines from stdout."""
        monkeypatch.setenv("SHOOTING_STAR_MODE", "dev")
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.chdir(tmp_path)
        settings = Settings()
        assert settings.log_format is LogFormat.JSON

        # structlog caches loggers per name on first use; reset so this test's
        # configuration takes effect regardless of prior test order.
        structlog.reset_defaults()
        configure_logging(settings)

        log = get_logger("test_capture")
        log.info("kite_login", api_key="hunter2", symbol="NIFTY")

        # Flush stdlib logging so the buffer is drained before capsys reads.
        for handler in logging.getLogger().handlers:
            handler.flush()

        captured = capsys.readouterr()
        return [json.loads(line) for line in captured.out.splitlines() if line.strip()]

    def test_json_output_redacts(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        records = self._capture_json(monkeypatch, tmp_path, capsys)
        assert len(records) == 1
        rec = records[0]
        assert rec["event"] == "kite_login"
        assert rec["api_key"] == "<redacted>"
        assert rec["symbol"] == "NIFTY"
        assert rec["level"] == "info"
        assert "timestamp" in rec

    def test_configure_is_idempotent(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("SHOOTING_STAR_MODE", "dev")
        monkeypatch.chdir(tmp_path)
        settings = Settings()
        configure_logging(settings)
        configure_logging(settings)  # must not raise
        structlog.reset_defaults()


class TestAuditLogPath:
    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        base = tmp_path / "audit"
        p = audit_log_path(base, "orders")
        assert base.is_dir()
        assert p == base / "orders.jsonl"
