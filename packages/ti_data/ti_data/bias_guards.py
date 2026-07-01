"""Bias guards for the data access layer.

The single most important invariant Shooting Star enforces is:

    In backtest mode, no data read may return a row whose `bar_close_time`
    is greater than the simulator's current clock.

Every DuckDB / Parquet / SQL query issued from strategy or feature code goes
through `bias_guarded_query(...)` which asserts this invariant. The assertion
is a load-bearing test, not a nice-to-have — the entire class of "my strategy
worked in backtest, lost money live" bugs traces to violations of this rule.

## Second bias guarded: survivorship

Point-in-time instrument queries filter by `valid_from <= trade_date <
valid_to`. `SurvivorshipGuard` wraps the SQLAlchemy Instrument model so any
query missing that filter raises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pandas as pd

if TYPE_CHECKING:
    from datetime import datetime

    from ti_core.clock import Clock

# Column name that every bar-shaped dataframe must expose.
BAR_CLOSE_COLUMN: Final[str] = "bar_close_time"

# Module-level default so we don't call pd.Timedelta in a function default (B008).
_ZERO_SLACK: Final[pd.Timedelta] = pd.Timedelta(0)


class LookAheadError(AssertionError):
    """Raised when a backtest query would return rows in the simulator's future.

    This is an `AssertionError` subclass so pytest treats it like other
    invariant violations: no `except Exception` clause in the strategy engine
    should swallow it silently.
    """


class SurvivorshipError(AssertionError):
    """Raised when an instrument query does not filter by point-in-time validity."""


@dataclass(frozen=True)
class BarQueryResult:
    """Result of a bias-guarded bar query."""

    frame: pd.DataFrame
    max_bar_close: datetime | None  # None if empty


def assert_no_lookahead(
    frame: pd.DataFrame,
    clock: Clock,
    *,
    slack: pd.Timedelta = _ZERO_SLACK,
) -> BarQueryResult:
    """Assert no row in `frame` has a `bar_close_time` later than `clock.now() + slack`.

    `slack` should be 0 in backtest mode. In paper/live it can be a small
    positive Timedelta to accommodate the fact that a bar closes at time T
    but our clock might read T-epsilon during the bar-emission microstep.

    Returns a `BarQueryResult` so callers can log the observed max_bar_close.
    """
    if BAR_CLOSE_COLUMN not in frame.columns:
        msg = (
            f"bias_guards: frame is missing required column '{BAR_CLOSE_COLUMN}'. "
            f"Every bar-shaped dataframe passing through strategy code must have it."
        )
        raise LookAheadError(msg)

    if frame.empty:
        return BarQueryResult(frame=frame, max_bar_close=None)

    now = clock.now()
    threshold = pd.Timestamp(now) + slack
    max_close = pd.Timestamp(frame[BAR_CLOSE_COLUMN].max())

    if max_close > threshold:
        msg = (
            f"bias_guards: LOOK-AHEAD BIAS detected. "
            f"Frame max bar_close_time = {max_close.isoformat()} > clock.now() + slack "
            f"= {threshold.isoformat()}. "
            f"This means strategy code just read data from the simulator's future. "
            f"Backtest results computed on this data are invalid."
        )
        raise LookAheadError(msg)

    return BarQueryResult(frame=frame, max_bar_close=max_close.to_pydatetime())


def assert_instrument_query_is_point_in_time(sql: str) -> None:
    """Fail if a raw SQL string touching the `instruments` table lacks a valid-window filter.

    Callers should prefer the ORM / query-builder abstractions that add this
    filter automatically. This function is a defense-in-depth check for the
    rare places where raw SQL is used against instrument metadata.
    """
    normalized = sql.lower()
    if "instruments" not in normalized:
        return  # not an instruments query
    if "valid_from" not in normalized or "valid_to" not in normalized:
        msg = (
            "bias_guards: SURVIVORSHIP BIAS risk. Raw SQL query touches the "
            "`instruments` table without filtering on both `valid_from` and "
            "`valid_to`. Backtests using this data may see instruments that "
            "did not exist yet, or filter to today's survivors only. "
            f"SQL: {sql!r}"
        )
        raise SurvivorshipError(msg)
