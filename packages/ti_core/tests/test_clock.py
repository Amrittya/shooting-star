"""Tests for `ti_core.clock`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from ti_core.clock import IST, ManualClock, SystemClock


class TestSystemClock:
    def test_now_is_utc_aware(self) -> None:
        t = SystemClock().now()
        assert t.tzinfo is not None
        assert t.utcoffset() == timedelta(0)

    def test_now_ist_matches_now_utc(self) -> None:
        clock = SystemClock()
        utc = clock.now()
        ist = clock.now_ist()
        # 5:30 diff in seconds = 19800
        assert (ist.utcoffset() or timedelta(0)).total_seconds() == 19800
        # Same instant on the timeline (allow ±1s for clock progression between calls)
        assert abs((ist - utc).total_seconds()) < 1

    @freeze_time("2026-07-02 10:00:00", tz_offset=0)
    def test_market_open_on_weekday_mid_session(self) -> None:
        # 10:00 UTC = 15:30 IST — market closes exactly at 15:30 IST → False.
        # Use 09:00 UTC = 14:30 IST → True.
        with freeze_time("2026-07-02 09:00:00"):
            assert SystemClock().is_market_open() is True

    def test_market_closed_on_weekend(self) -> None:
        # 2026-07-04 is a Saturday.
        with freeze_time("2026-07-04 05:00:00"):  # 10:30 IST Sat
            assert SystemClock().is_market_open() is False

    def test_market_closed_before_open(self) -> None:
        # 03:00 UTC = 08:30 IST (weekday) → market not open yet.
        with freeze_time("2026-07-02 03:00:00"):  # Thursday
            assert SystemClock().is_market_open() is False

    def test_market_closed_after_close(self) -> None:
        # 12:00 UTC = 17:30 IST (weekday) → market closed.
        with freeze_time("2026-07-02 12:00:00"):
            assert SystemClock().is_market_open() is False


class TestManualClock:
    def test_requires_tz_aware_start(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            ManualClock(datetime(2026, 1, 1))  # noqa: DTZ001

    def test_converts_to_utc_internally(self) -> None:
        start_ist = datetime(2026, 7, 2, 15, 30, tzinfo=IST)
        clock = ManualClock(start_ist)
        assert clock.now().tzinfo == UTC
        assert clock.now() == start_ist.astimezone(UTC)

    def test_advance_moves_forward(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 0, 0, tzinfo=UTC))
        clock.advance(timedelta(hours=1))
        assert clock.now() == datetime(2026, 7, 2, 1, 0, tzinfo=UTC)

    def test_advance_rejects_negative(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 0, 0, tzinfo=UTC))
        with pytest.raises(ValueError, match="non-negative"):
            clock.advance(timedelta(seconds=-1))

    def test_set_forward_ok(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 0, 0, tzinfo=UTC))
        clock.set(datetime(2026, 7, 2, 5, 0, tzinfo=UTC))
        assert clock.now().hour == 5

    def test_set_backward_rejected(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 5, 0, tzinfo=UTC))
        with pytest.raises(ValueError, match="cannot move backward"):
            clock.set(datetime(2026, 7, 2, 4, 0, tzinfo=UTC))

    def test_set_rejects_naive(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 0, 0, tzinfo=UTC))
        with pytest.raises(ValueError, match="timezone-aware"):
            clock.set(datetime(2026, 7, 2, 1, 0))  # noqa: DTZ001

    def test_is_market_open_uses_simulated_time(self) -> None:
        # Thursday 09:00 UTC = 14:30 IST → market open.
        clock = ManualClock(datetime(2026, 7, 2, 9, 0, tzinfo=UTC))
        assert clock.is_market_open() is True
        # Advance to 11:00 UTC = 16:30 IST → market closed.
        clock.advance(timedelta(hours=2))
        assert clock.is_market_open() is False
