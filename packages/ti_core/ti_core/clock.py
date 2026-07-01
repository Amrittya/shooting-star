"""Clock abstraction.

The single most important primitive for eliminating look-ahead bias.

In live/paper mode: `now()` reads the wall clock (UTC).
In backtest mode: `now()` returns the simulator's current simulated timestamp.

All time-sensitive code — feature computation, bar aggregation, signal
evaluation, backtest data queries — MUST read time via a `Clock` instance,
not via `datetime.now()` directly. The `bias_guards` module in `ti_backtest`
asserts this at query boundaries.

## Time zone policy

**All timestamps are UTC.** Convert to Asia/Kolkata (IST) only at display
boundaries (CLI output, dashboard). The IST market session (09:15-15:30) is
computed from UTC by adding +05:30. Never store IST timestamps.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta, tzinfo
from typing import Final
from zoneinfo import ZoneInfo

IST: Final[tzinfo] = ZoneInfo("Asia/Kolkata")

# Regular NSE equity session in IST. Options F&O session is the same window.
MARKET_OPEN_IST: Final[tuple[int, int]] = (9, 15)  # HH, MM
MARKET_CLOSE_IST: Final[tuple[int, int]] = (15, 30)


class Clock(ABC):
    """Abstract clock. Injected everywhere time is needed."""

    @abstractmethod
    def now(self) -> datetime:
        """Current time, in UTC. Never naive."""

    def now_ist(self) -> datetime:
        """Current time, converted to IST."""
        return self.now().astimezone(IST)

    def is_market_open(self, now: datetime | None = None) -> bool:
        """True iff the current time falls inside the NSE equity/F&O regular session.

        Does NOT account for exchange holidays; the holiday calendar lives in
        `ti_data`. Callers that need holiday-aware answers should compose with
        an `ExchangeCalendar`.
        """
        current = (now or self.now()).astimezone(IST)
        if current.weekday() >= 5:  # 5=Sat, 6=Sun
            return False
        open_h, open_m = MARKET_OPEN_IST
        close_h, close_m = MARKET_CLOSE_IST
        open_at = current.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
        close_at = current.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
        return open_at <= current < close_at


class SystemClock(Clock):
    """Real wall-clock. Used in live and paper modes."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class ManualClock(Clock):
    """Manually-advanced clock. Used in backtests and unit tests.

    Not thread-safe; each backtest engine owns its own instance.
    """

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            msg = "ManualClock requires a timezone-aware start timestamp"
            raise ValueError(msg)
        self._t = start.astimezone(UTC)

    def now(self) -> datetime:
        return self._t

    def advance(self, delta: timedelta) -> None:
        """Advance the simulated clock by `delta`."""
        if delta < timedelta(0):
            msg = "ManualClock.advance requires a non-negative delta"
            raise ValueError(msg)
        self._t += delta

    def set(self, t: datetime) -> None:
        """Set the simulated clock to `t` (must not move backward)."""
        if t.tzinfo is None:
            msg = "ManualClock.set requires a timezone-aware timestamp"
            raise ValueError(msg)
        new_t = t.astimezone(UTC)
        if new_t < self._t:
            msg = f"ManualClock.set cannot move backward: {new_t} < {self._t}"
            raise ValueError(msg)
        self._t = new_t
