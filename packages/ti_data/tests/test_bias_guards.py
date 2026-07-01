"""Tests for `ti_data.bias_guards`.

Bias-guard invariants are load-bearing — a single missed test here could
silently reintroduce the look-ahead / survivorship bugs the whole design
exists to prevent. Coverage is dense on purpose.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from ti_core.clock import ManualClock
from ti_data.bias_guards import (
    BAR_CLOSE_COLUMN,
    LookAheadError,
    SurvivorshipError,
    assert_instrument_query_is_point_in_time,
    assert_no_lookahead,
)


def _bars(times: list[datetime]) -> pd.DataFrame:
    return pd.DataFrame({BAR_CLOSE_COLUMN: times, "close": [100.0] * len(times)})


class TestAssertNoLookahead:
    def test_frame_in_the_past_passes(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = _bars([datetime(2026, 7, 2, 11, 0, tzinfo=UTC)])
        result = assert_no_lookahead(frame, clock)
        assert result.max_bar_close == datetime(2026, 7, 2, 11, 0, tzinfo=UTC)

    def test_frame_at_now_passes(self) -> None:
        now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)
        clock = ManualClock(now)
        frame = _bars([now])
        assert_no_lookahead(frame, clock)  # equality is OK

    def test_frame_in_the_future_raises(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = _bars([datetime(2026, 7, 2, 12, 1, tzinfo=UTC)])  # 1 min ahead
        with pytest.raises(LookAheadError, match="LOOK-AHEAD BIAS"):
            assert_no_lookahead(frame, clock)

    def test_slack_allows_small_lead(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = _bars([datetime(2026, 7, 2, 12, 0, 30, tzinfo=UTC)])  # 30s ahead
        # Slack of 1 min → passes.
        assert_no_lookahead(frame, clock, slack=pd.Timedelta(minutes=1))

    def test_slack_zero_by_default(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = _bars([datetime(2026, 7, 2, 12, 0, 1, tzinfo=UTC)])  # 1s ahead
        with pytest.raises(LookAheadError):
            assert_no_lookahead(frame, clock)

    def test_empty_frame_passes(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = pd.DataFrame({BAR_CLOSE_COLUMN: [], "close": []})
        result = assert_no_lookahead(frame, clock)
        assert result.max_bar_close is None

    def test_missing_column_raises(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = pd.DataFrame({"wrong_col": [datetime.now(tz=UTC)]})
        with pytest.raises(LookAheadError, match="missing required column"):
            assert_no_lookahead(frame, clock)

    def test_advance_clock_lets_previously_future_pass(self) -> None:
        clock = ManualClock(datetime(2026, 7, 2, 12, 0, tzinfo=UTC))
        frame = _bars([datetime(2026, 7, 2, 12, 30, tzinfo=UTC)])
        with pytest.raises(LookAheadError):
            assert_no_lookahead(frame, clock)
        clock.advance(timedelta(hours=1))
        # Now the frame is entirely in the past.
        assert_no_lookahead(frame, clock)


class TestSurvivorshipGuard:
    def test_non_instruments_query_passes(self) -> None:
        assert_instrument_query_is_point_in_time("SELECT * FROM trades WHERE id = 1")

    def test_instruments_query_with_both_filters_passes(self) -> None:
        assert_instrument_query_is_point_in_time(
            "SELECT * FROM instruments WHERE valid_from <= :t AND (valid_to IS NULL OR :t < valid_to)"
        )

    def test_instruments_query_missing_valid_from_raises(self) -> None:
        with pytest.raises(SurvivorshipError, match="SURVIVORSHIP BIAS"):
            assert_instrument_query_is_point_in_time(
                "SELECT * FROM instruments WHERE valid_to > NOW()"
            )

    def test_instruments_query_missing_valid_to_raises(self) -> None:
        with pytest.raises(SurvivorshipError):
            assert_instrument_query_is_point_in_time(
                "SELECT * FROM instruments WHERE valid_from < NOW()"
            )

    def test_instruments_query_missing_both_raises(self) -> None:
        with pytest.raises(SurvivorshipError):
            assert_instrument_query_is_point_in_time("SELECT * FROM instruments")

    def test_case_insensitive(self) -> None:
        # Should still catch even with weird casing.
        with pytest.raises(SurvivorshipError):
            assert_instrument_query_is_point_in_time("SELECT * FROM Instruments")
