"""SQLAlchemy models for the metadata database (SQLite locally, Postgres later).

Only *metadata* lives here: instrument definitions, trade records, run bookkeeping,
kill-switch state. Bulk time-series data (bars, ticks, chains) lives in Parquet
with DuckDB views on top — SQLite would drown.

Point-in-time correctness:
- The `Instrument` table stores `valid_from` and `valid_to` so backtests can
  query the instrument universe as it existed on a specific date. Do NOT drop
  or update instrument rows in place; insert a new row with a fresh
  `valid_from` and close the old one's `valid_to`.
"""

from __future__ import annotations

# SQLAlchemy Mapped[...] annotations are inspected at class-definition time,
# so datetime/Decimal must be importable at runtime — do NOT move to
# TYPE_CHECKING. ruff's TC003 is a false positive here.
from datetime import datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Root ORM base."""


class Instrument(Base):
    """One row per (instrument, valid_from) point-in-time snapshot.

    A single tradeable instrument (e.g. NIFTY24JUL22500CE) may appear multiple
    times with non-overlapping `[valid_from, valid_to)` windows if its
    definition (lot size, freeze qty) changes over time. Backtests filter by
    `valid_from <= trade_date < valid_to`.
    """

    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Kite instrument_token (numeric ID assigned by Zerodha); may be re-used
    # across historical instruments, so it's NOT a primary key.
    instrument_token: Mapped[int] = mapped_column(index=True)
    tradingsymbol: Mapped[str] = mapped_column(String(64), index=True)
    exchange: Mapped[str] = mapped_column(String(8))  # NSE | NFO | BFO | BSE
    segment: Mapped[str] = mapped_column(String(16))  # NSE | NFO-OPT | NFO-FUT | ...
    instrument_type: Mapped[str] = mapped_column(String(8))  # EQ | FUT | CE | PE
    name: Mapped[str] = mapped_column(String(128))

    # F&O specifics (nullable for equity rows)
    expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    strike: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    lot_size: Mapped[int] = mapped_column()

    # Tick size for the instrument (paise for equity, ₹ for options)
    tick_size: Mapped[Decimal] = mapped_column(Numeric(18, 6))

    # Point-in-time window
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("ix_instruments_symbol_valid", "tradingsymbol", "valid_from"),
        Index("ix_instruments_token_valid", "instrument_token", "valid_from"),
        UniqueConstraint("instrument_token", "valid_from", name="uq_instruments_token_valid_from"),
    )


class Run(Base):
    """A single backtest, paper, or live session.

    Anything the system does (trades placed, agent artifacts emitted, kill
    switches triggered) is scoped to a Run so post-hoc analysis can slice.
    """

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(16))  # backtest | paper | live
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config_hash: Mapped[str] = mapped_column(
        String(64)
    )  # sha256 of full config for reproducibility
    notes: Mapped[str | None] = mapped_column(String(1024))

    trades: Mapped[list[Trade]] = relationship(back_populates="run")


class Trade(Base):
    """A single realized (opened + closed) trade.

    Open positions live in the strategy engine's memory + broker; only closed
    trades land here as immutable records.
    """

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    tradingsymbol: Mapped[str] = mapped_column(String(64), index=True)
    exchange: Mapped[str] = mapped_column(String(8))

    side: Mapped[str] = mapped_column(String(8))  # BUY | SELL
    quantity: Mapped[int] = mapped_column()
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Gross PnL before charges; net PnL is gross - charges.
    gross_pnl_inr: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    charges_inr: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    net_pnl_inr: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    # Regulatory-regime tag at trade date (for the ADR-0002 overlay).
    regulatory_regime: Mapped[str] = mapped_column(String(32), index=True)

    # Free-form structured metadata (regime tag, event tags, strategy version, etc.)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    run: Mapped[Run] = relationship(back_populates="trades")


class KillSwitchState(Base):
    """Persistent kill-switch flags. One row per (scope, level).

    Scope: 'global' | strategy_id.
    Level: 'daily' | 'weekly' | 'per_strategy'.
    """

    __tablename__ = "kill_switch_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    armed: Mapped[bool] = mapped_column(default=False)
    reason: Mapped[str | None] = mapped_column(String(512))

    __table_args__ = (UniqueConstraint("scope", "level", name="uq_kill_scope_level"),)


class AgentArtifact(Base):
    """L1/L2/L3 agent output — the artifact-not-command boundary (ADR-0003).

    The strategy engine reads agent artifacts (event tags, regime tags,
    proposals) as inputs; agents never write orders directly.
    """

    __tablename__ = "agent_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    tier: Mapped[str] = mapped_column(String(4))  # L1 | L2 | L3
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON)

    # LLM audit info
    model: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None] = mapped_column()
    output_tokens: Mapped[int | None] = mapped_column()
    cost_inr: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
