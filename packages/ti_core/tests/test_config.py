"""Tests for `ti_core.config`."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from pydantic import SecretStr, ValidationError
from ti_core.config import LogFormat, RunMode, Settings, reset_settings_for_testing

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    reset_settings_for_testing()


def test_defaults_are_sensible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With an empty env, all defaults load and represent a safe dev config."""
    # Strip anything the developer may have exported globally.
    for var in [
        "SHOOTING_STAR_MODE",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "KITE_API_KEY",
        "KITE_API_SECRET",
        "ANTHROPIC_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)  # no .env file present

    s = Settings()
    assert s.mode is RunMode.DEV
    assert s.log_level == "INFO"
    assert s.log_format is LogFormat.JSON
    assert s.kite_api_key is None
    assert s.anthropic_api_key is None
    # Financial defaults are positive
    assert s.total_capital_inr > 0
    assert s.max_net_delta_inr_per_1pct_nifty > 0


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Env vars override defaults; secrets wrap in SecretStr."""
    monkeypatch.setenv("SHOOTING_STAR_MODE", "paper")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "console")
    monkeypatch.setenv("KITE_API_KEY", "test-key-xyz")
    monkeypatch.setenv("DAILY_LOSS_KILL_PCT", "2.5")
    monkeypatch.chdir(tmp_path)

    s = Settings()
    assert s.mode is RunMode.PAPER
    assert s.log_level == "DEBUG"
    assert s.log_format is LogFormat.CONSOLE
    assert isinstance(s.kite_api_key, SecretStr)
    assert s.kite_api_key.get_secret_value() == "test-key-xyz"
    assert s.daily_loss_kill_pct == Decimal("2.5")


def test_kill_pct_bounds_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Kill switch percentages must be in (0, 100]."""
    monkeypatch.setenv("DAILY_LOSS_KILL_PCT", "0")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError):
        Settings()

    monkeypatch.setenv("DAILY_LOSS_KILL_PCT", "150")
    with pytest.raises(ValidationError):
        Settings()


def test_negative_capital_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Capital allocations must be strictly positive."""
    monkeypatch.setenv("TOTAL_CAPITAL_INR", "-1")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValidationError):
        Settings()


def test_require_broker_ok_in_dev(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Dev mode doesn't require broker credentials."""
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    Settings().require_broker()  # must not raise


def test_require_broker_fails_in_paper_without_creds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Paper mode without KITE_API_KEY must fail loudly at startup."""
    monkeypatch.setenv("SHOOTING_STAR_MODE", "paper")
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.delenv("KITE_API_SECRET", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="KITE_API_KEY"):
        Settings().require_broker()


def test_require_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """LLM guard fails when the key is missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        Settings().require_llm()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-abc")
    Settings().require_llm()  # ok
