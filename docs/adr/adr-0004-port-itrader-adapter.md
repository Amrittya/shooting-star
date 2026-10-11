# ADR-0004 — Port iTrader ZerodhaBroker as interim PykiteBroker

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Amrittya, Claude

## Context

The predecessor project (iTrader)
contains a production-tested Zerodha adapter
(`itrader-brokers/itrader_brokers/zerodha/adapter.py`) that has been running
live. Analysis identified it as high-quality (comprehensive Kite feature
wrapping, async via `asyncio.to_thread`, clean type hierarchy) with specific
gaps:

1. **Order state mapping is incomplete** — maps 5 of Kite's 12+ transitional
   states. Missing: `PUT ORDER REQ RECEIVED`, `VALIDATION PENDING`,
   `OPEN PENDING`, `MODIFY VALIDATION PENDING`, `MODIFY PENDING`,
   `TRIGGER PENDING`, plus post-only variants. A `VALIDATION PENDING` order
   currently maps to `PENDING` and could be misclassified as "not yet sent"
   and retried — a data-loss risk in live trading.
2. **No rate-limit queue** — caller must self-throttle. Kite enforces 10
   orders/sec, 400/min, 5000/day, 3 hist-data/sec, 1 quote/sec.
3. **No reconnect reconciliation** — if an order was placed just before
   disconnect, it might land on the broker but locally appear failed.
4. **Credentials stored in plaintext in `__init__`** — coredump / log-scrape
   risk.
5. **References deprecated `bracket` (BO) order variety** — Zerodha deprecated
   this ~2020; must use `iceberg` + `co` + `auction`.
6. **No option chain retrieval method** — needs adding.

The Rust nautilus-kite adapter (Phase 4) will take 3-4 months. We need paper
trading working in weeks, not months.

## Decision

**Port the iTrader `ZerodhaBroker` into `packages/ti_execution/pykit_broker.py`
with the following fixes on top:**

1. **Complete order state mapping** — all 12+ Kite states mapped explicitly.
2. **Rate-limit queue** — per-endpoint token buckets. Orders 10/sec + 400/min
   + 5000/day; historical 3/sec; quote 1/sec.
3. **Reconnect reconciliation stub** — on reconnect, fetch all broker orders,
   diff against local position DB, reconcile discrepancies.
4. **Credential handling** — read from env vars only via `ti_core.config`,
   never stored in instance attributes, redacted in logs.
5. **Order varieties** — support `regular`, `amo`, `co`, `iceberg`, `auction`.
   `bracket` explicitly rejected with a clear error.
6. **Option chain method** — add `get_option_chain(underlying, expiry)`.

Interface: implement the same `BrokerAdapter` protocol that the future
nautilus-kite adapter will implement. Strategies target the protocol; swap
implementations without touching strategy code.

Scope: paper trading only in Phase 2. Live trading gated behind Phase 7
verification (see plan doc §8).

## Consequences

**Positive:**
- Fast path to paper trading (weeks, not months).
- Reuses production-tested Kite integration knowledge (auth flow,
  WebSocket handling, instrument dump caching).
- Six documented improvements over iTrader's version make it strictly better
  than a raw port.

**Negative:**
- Two adapter implementations to maintain (interim Python + eventual Rust).
  Mitigated by shared `BrokerAdapter` protocol.
- Some divergence risk between paper-trading behavior on `PykiteBroker` and
  Rust adapter behavior. Phase 7 verification includes a paper-vs-live
  divergence gate before live deployment.

## Alternatives Considered

- **Wait for Rust adapter.** 3-4 months of no paper trading. Rejected.
- **Use kiteconnect directly, no adapter layer.** Couples strategies to
  Kite's API surface. Rejected — the whole point of the adapter is to make
  brokers swappable.
- **Fresh rewrite, not a port.** Loses production knowledge encoded in
  iTrader's implementation. Rejected.

## Follow-ups

- Verify autobahn 26.x compatibility with kiteconnect 5.2 (kiteconnect pins
  autobahn 19.11 by default; we override to 26.6 to fix PYSEC-2020-25).
  See ADR-0005.
- Port timeline: 2-3 days of implementation + 1 week of unit-test coverage
  against a mocked KiteConnect client (no live API calls in tests).
