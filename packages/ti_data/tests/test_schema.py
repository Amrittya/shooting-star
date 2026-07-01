"""Tests for `ti_data.storage.schema`.

Purpose: verify the ORM models can be created, that point-in-time constraints
are honored, and that the composite indexes make sense. We use an in-memory
SQLite DB per test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ti_data.storage.schema import (
    AgentArtifact,
    Base,
    Instrument,
    KillSwitchState,
    Run,
    Trade,
)

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


class TestInstrument:
    def test_insert_and_query(self, session: Session) -> None:
        inst = Instrument(
            instrument_token=256265,
            tradingsymbol="NIFTY 50",
            exchange="NSE",
            segment="NSE",
            instrument_type="EQ",
            name="Nifty 50",
            expiry=None,
            strike=None,
            lot_size=1,
            tick_size=Decimal("0.05"),
            valid_from=datetime(2024, 1, 1, tzinfo=UTC),
            valid_to=None,
        )
        session.add(inst)
        session.commit()

        found = session.execute(
            select(Instrument).where(Instrument.tradingsymbol == "NIFTY 50")
        ).scalar_one()
        assert found.instrument_token == 256265
        assert found.lot_size == 1
        assert found.valid_to is None

    def test_pit_snapshots_of_same_symbol(self, session: Session) -> None:
        """A single tradingsymbol can have multiple non-overlapping valid windows."""
        # Row 1: lot_size 75 (initial Nov-2024 SEBI value).
        session.add(
            Instrument(
                instrument_token=99999,
                tradingsymbol="NIFTY25JUL22500CE",
                exchange="NFO",
                segment="NFO-OPT",
                instrument_type="CE",
                name="NIFTY JUL 22500 CE",
                expiry=datetime(2025, 7, 31, tzinfo=UTC),
                strike=Decimal("22500"),
                lot_size=75,
                tick_size=Decimal("0.05"),
                valid_from=datetime(2024, 11, 20, tzinfo=UTC),
                valid_to=datetime(2025, 5, 1, tzinfo=UTC),
            )
        )
        # Row 2: lot_size 65 (after SEBI rebalance).
        session.add(
            Instrument(
                instrument_token=99999,
                tradingsymbol="NIFTY25JUL22500CE",
                exchange="NFO",
                segment="NFO-OPT",
                instrument_type="CE",
                name="NIFTY JUL 22500 CE",
                expiry=datetime(2025, 7, 31, tzinfo=UTC),
                strike=Decimal("22500"),
                lot_size=65,
                tick_size=Decimal("0.05"),
                valid_from=datetime(2025, 5, 1, tzinfo=UTC),
                valid_to=None,
            )
        )
        session.commit()

        rows = (
            session.execute(
                select(Instrument).where(Instrument.tradingsymbol == "NIFTY25JUL22500CE")
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        assert {r.lot_size for r in rows} == {65, 75}

    def test_duplicate_token_same_valid_from_rejected(self, session: Session) -> None:
        """The (instrument_token, valid_from) uniqueness constraint holds."""
        common = {
            "instrument_token": 12345,
            "tradingsymbol": "SYM",
            "exchange": "NSE",
            "segment": "NSE",
            "instrument_type": "EQ",
            "name": "Sym",
            "expiry": None,
            "strike": None,
            "lot_size": 1,
            "tick_size": Decimal("0.05"),
            "valid_from": datetime(2024, 1, 1, tzinfo=UTC),
            "valid_to": None,
        }
        session.add(Instrument(**common))
        session.add(Instrument(**common))
        with pytest.raises(IntegrityError):
            session.commit()


class TestRunAndTrade:
    def test_relationship(self, session: Session) -> None:
        run = Run(
            run_id="test-2026-07-02-01",
            mode="backtest",
            started_at=datetime(2026, 7, 2, 0, 0, tzinfo=UTC),
            config_hash="abc123",
            notes=None,
        )
        session.add(run)
        session.flush()

        trade = Trade(
            run_id=run.id,
            strategy_id="orb_nifty_v1",
            tradingsymbol="NIFTY 50",
            exchange="NSE",
            side="BUY",
            quantity=65,
            entry_time=datetime(2026, 7, 2, 9, 30, tzinfo=UTC),
            entry_price=Decimal("22500.00"),
            exit_time=datetime(2026, 7, 2, 10, 30, tzinfo=UTC),
            exit_price=Decimal("22550.00"),
            gross_pnl_inr=Decimal("3250.00"),
            charges_inr=Decimal("120.00"),
            net_pnl_inr=Decimal("3130.00"),
            regulatory_regime="post-2026-04-01",
        )
        session.add(trade)
        session.commit()

        assert len(run.trades) == 1
        assert run.trades[0].net_pnl_inr == Decimal("3130.00")


class TestKillSwitch:
    def test_unique_scope_level(self, session: Session) -> None:
        session.add(KillSwitchState(scope="global", level="daily", armed=False))
        session.add(KillSwitchState(scope="global", level="daily", armed=True))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_different_scope_level_allowed(self, session: Session) -> None:
        session.add(KillSwitchState(scope="global", level="daily", armed=False))
        session.add(KillSwitchState(scope="global", level="weekly", armed=False))
        session.add(KillSwitchState(scope="orb_nifty_v1", level="per_strategy", armed=False))
        session.commit()
        rows = session.execute(select(KillSwitchState)).scalars().all()
        assert len(rows) == 3


class TestAgentArtifact:
    def test_stores_llm_audit_info(self, session: Session) -> None:
        art = AgentArtifact(
            agent_name="news_event",
            tier="L1",
            artifact_type="EventTag",
            created_at=datetime(2026, 7, 2, 7, 30, tzinfo=UTC),
            payload_json={"event": "RBI_policy", "impact": "high"},
            model="claude-haiku-4-5",
            input_tokens=1200,
            output_tokens=150,
            cost_inr=Decimal("0.85"),
        )
        session.add(art)
        session.commit()
        found = session.execute(
            select(AgentArtifact).where(AgentArtifact.artifact_type == "EventTag")
        ).scalar_one()
        assert found.payload_json["event"] == "RBI_policy"
        assert found.cost_inr == Decimal("0.85")
