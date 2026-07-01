# ADR-0002 — Regulatory-regime overlay for backtests

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Amrittya, Claude

## Context

Indian equity derivatives underwent material regulatory change between Oct 2024
and Apr 2026. Any backtest that treats those years as a single regime will
overstate strategy edge and hide fragility.

Confirmed from SEBI circular **SEBI/HO/MRD/TPD-1/P/CIR/2024/132** (1 Oct 2024)
and Budget 2026:

| Date          | Change                                                            |
|---------------|-------------------------------------------------------------------|
| 2024-11-20    | Weekly expiries rationalized to one per exchange (NIFTY / SENSEX only). BankNifty / FinNifty / MidcpNifty weekly options **discontinued**. Contract size raised to ₹15-20L. +2% ELM on short options on expiry day (applies at entry time, not just morning review). |
| 2025-02-01    | Upfront option premium collection from buyers. Calendar-spread expiry-day benefit removed. |
| 2025-04-01    | Intraday position-limit monitoring (≥4 random snapshots per day). |
| 2026-04-01    | STT on options-sell increased from 0.1% → 0.15% (was 0.0625% pre-Oct-2024). |

## Decision

**Every backtest report emits per-regulatory-regime P&L**, keyed by trade
timestamp. The charges model (`ti_risk/charges.py`) is date-parameterized so
each trade's STT is computed with the rate active on its trade date. Five
regime buckets, split at the four boundary dates above.

Kill switches trip on **cost-normalized loss**, not gross P&L, so regulatory
regime changes that shift the charges baseline don't silently push books past
thresholds.

## Consequences

**Positive:**
- Strategies that "worked" only under pre-Nov-2024 rules or pre-STT-hike
  economics are visible as such in every report.
- Backward-compatible: existing historical data does not need re-labeling; the
  overlay is computed at report time.

**Negative:**
- Extra complexity in the charges module. Test coverage must include the
  boundary dates explicitly (unit tests hit each regime).
- Any strategy that shows a large per-regime P&L delta must be sanity-checked
  for regime-conditional overfitting, not just celebrated for "adapting."

## Follow-ups

- Verify SEBI has not published further post-Apr-2026 amendments before
  first paper-trade launch.
- Consider adding a similar overlay for exchange-fee changes (BFO vs NFO
  fee schedule shifts).
