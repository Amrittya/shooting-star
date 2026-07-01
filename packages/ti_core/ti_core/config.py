"""Application configuration for Shooting Star.

All settings are loaded from environment variables (via a `.env` file or
process environment). Secrets never appear in log lines: `SecretStr` values
are auto-redacted by structlog processors.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RunMode(StrEnum):
    """Runtime mode for Shooting Star.

    - `dev`: local development; no broker connectivity assumed.
    - `paper`: paper trading against Kite (real market data, simulated orders).
    - `live`: live trading. Extra guardrails apply.
    """

    DEV = "dev"
    PAPER = "paper"
    LIVE = "live"


class LogFormat(StrEnum):
    """Structured (JSON) vs. human-readable (console) log output."""

    JSON = "json"
    CONSOLE = "console"


class Settings(BaseSettings):
    """Top-level settings loaded from env vars.

    Any field with a default is optional; fields without defaults must be
    set in the environment before `Settings()` can be constructed. That
    fail-fast behavior is deliberate — a mis-configured trading system
    should refuse to start.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
        # SHOOTING_STAR_MODE, LOG_LEVEL, KITE_API_KEY, etc.
    )

    # --- Runtime ---
    mode: RunMode = Field(default=RunMode.DEV, alias="SHOOTING_STAR_MODE")

    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    log_format: LogFormat = Field(default=LogFormat.JSON, alias="LOG_FORMAT")
    log_file: Path | None = Field(default=None, alias="LOG_FILE")

    # --- Storage ---
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    duckdb_path: Path = Field(default=Path("./data/shooting-star.duckdb"), alias="DUCKDB_PATH")
    sqlite_path: Path = Field(default=Path("./data/metadata.db"), alias="SQLITE_PATH")
    parquet_dir: Path = Field(default=Path("./data/parquet"), alias="PARQUET_DIR")

    # --- Event bus (Redis) ---
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # --- Broker (Zerodha Kite) — optional in dev, required in paper/live ---
    kite_api_key: SecretStr | None = Field(default=None, alias="KITE_API_KEY")
    kite_api_secret: SecretStr | None = Field(default=None, alias="KITE_API_SECRET")
    kite_access_token: SecretStr | None = Field(default=None, alias="KITE_ACCESS_TOKEN")

    # --- LLM providers ---
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model_fast: str = Field(
        default="claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL_FAST"
    )
    anthropic_model_standard: str = Field(
        default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL_STANDARD"
    )
    anthropic_model_reasoning: str = Field(
        default="claude-opus-4-6", alias="ANTHROPIC_MODEL_REASONING"
    )

    # --- Agent budget caps ---
    agent_daily_budget_inr: Decimal = Field(default=Decimal("500"), alias="AGENT_DAILY_BUDGET_INR")
    agent_monthly_budget_inr: Decimal = Field(
        default=Decimal("10000"), alias="AGENT_MONTHLY_BUDGET_INR"
    )

    # --- Risk engine — portfolio greek limits (₹ per unit move) ---
    max_net_delta_inr_per_1pct_nifty: Decimal = Field(
        default=Decimal("15000"), alias="MAX_NET_DELTA_INR_PER_1PCT_NIFTY"
    )
    max_net_vega_inr_per_1_vol_point: Decimal = Field(
        default=Decimal("8000"), alias="MAX_NET_VEGA_INR_PER_1_VOL_POINT"
    )
    max_net_gamma_inr_per_1pct_nifty: Decimal = Field(
        default=Decimal("5000"), alias="MAX_NET_GAMMA_INR_PER_1PCT_NIFTY"
    )

    # --- Kill switches (% of capital) ---
    daily_loss_kill_pct: Decimal = Field(default=Decimal("3.0"), alias="DAILY_LOSS_KILL_PCT")
    weekly_loss_kill_pct: Decimal = Field(default=Decimal("6.0"), alias="WEEKLY_LOSS_KILL_PCT")
    per_strategy_loss_kill_pct: Decimal = Field(
        default=Decimal("4.0"), alias="PER_STRATEGY_LOSS_KILL_PCT"
    )

    # --- Capital allocation ---
    total_capital_inr: Decimal = Field(default=Decimal("2000000"), alias="TOTAL_CAPITAL_INR")
    option_buy_capital_inr: Decimal = Field(
        default=Decimal("20000"), alias="OPTION_BUY_CAPITAL_INR"
    )
    option_sell_capital_inr: Decimal = Field(
        default=Decimal("1980000"), alias="OPTION_SELL_CAPITAL_INR"
    )

    # --- Charges buffer (%) ---
    charges_buffer_pct: Decimal = Field(default=Decimal("10"), alias="CHARGES_BUFFER_PCT")

    # -----------------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------------

    @field_validator(
        "daily_loss_kill_pct",
        "weekly_loss_kill_pct",
        "per_strategy_loss_kill_pct",
        "charges_buffer_pct",
    )
    @classmethod
    def _kill_pct_range(cls, v: Decimal) -> Decimal:
        if not Decimal("0") < v <= Decimal("100"):
            msg = f"kill/buffer percentage must be in (0, 100]; got {v}"
            raise ValueError(msg)
        return v

    @field_validator(
        "max_net_delta_inr_per_1pct_nifty",
        "max_net_vega_inr_per_1_vol_point",
        "max_net_gamma_inr_per_1pct_nifty",
        "total_capital_inr",
        "option_buy_capital_inr",
        "option_sell_capital_inr",
        "agent_daily_budget_inr",
        "agent_monthly_budget_inr",
    )
    @classmethod
    def _positive_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            msg = f"amount must be positive; got {v}"
            raise ValueError(msg)
        return v

    def require_broker(self) -> None:
        """Fail fast if broker credentials are missing when running in paper/live."""
        if self.mode is RunMode.DEV:
            return
        if not self.kite_api_key or not self.kite_api_secret:
            msg = f"KITE_API_KEY and KITE_API_SECRET are required in {self.mode} mode"
            raise ValueError(msg)

    def require_llm(self) -> None:
        """Fail fast if the LLM API key is missing when it's needed."""
        if not self.anthropic_api_key:
            msg = "ANTHROPIC_API_KEY is required when the agent layer is enabled"
            raise ValueError(msg)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the process-wide settings singleton (cached after first call).

    Prefer this over constructing `Settings()` directly so that env parsing
    happens exactly once and downstream code can trust the values are stable.
    """
    global _settings  # noqa: PLW0603 — deliberate module-level singleton
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_for_testing() -> None:
    """Reset the cached settings. Only use in tests."""
    global _settings  # noqa: PLW0603
    _settings = None
