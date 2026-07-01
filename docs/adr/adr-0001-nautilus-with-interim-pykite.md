# ADR-0001 — Nautilus-trader as long-term core; interim PykiteBroker in Python

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Amrittya, Claude

## Context

Shooting Star needs an execution + backtesting engine that guarantees the same
code runs in backtest, paper, and live modes — historically the #1 source of
"my strategy worked in backtest, lost money live" failures for retail systematic
traders.

We evaluated:

- **Nautilus-trader** (Rust core, Python API; event-driven; explicit
  "same code backtest = live" guarantee). No built-in Zerodha adapter — must
  write a custom Rust adapter (3-4 month upfront investment).
- **QuantConnect Lean** (C# core, Python API). No Zerodha adapter either;
  same-code guarantee weaker than nautilus.
- **backtrader / vectorbt / zipline-reloaded** — either backtest-only or
  research-only; no production live-trading path.
- **Roll our own event-driven engine in Python** — 12+ months to reach parity
  with what nautilus gives us out of the box.

## Decision

**Long-term core: nautilus-trader 1.230+ with a custom Rust adapter for
Zerodha Kite** (`rust/nautilus-kite/`).

**Interim (Phase 2-3): pure-Python `PykiteBroker` in `packages/ti_execution/`,
ported from the existing iTrader Zerodha adapter**, exposing the same
`BrokerAdapter` interface. Strategies target the interface, not the concrete
adapter, so we swap when the Rust adapter is production-ready with zero
strategy changes.

**Research: VectorBT** for vectorized parameter sweeps on entry signals only
(vectorbt cannot represent stateful strategy logic honestly).

## Consequences

**Positive:**
- Same-code guarantee eliminates the biggest class of backtest-to-live bugs.
- Rust core gives correctness on the hot path (memory safety, deterministic
  event ordering) that Python cannot match.
- Adapter pattern lets us paper-trade in weeks, not months.

**Negative:**
- Rust adapter is a 3-4 month upfront cost. We accept this because:
  (a) the paper-trading path is not blocked on it (PykiteBroker unblocks it),
  (b) the correctness properties compound over years of live trading.
- Two adapters means two places to keep in sync. Mitigated by a single
  `BrokerAdapter` protocol both implement.
- Nautilus 1.230+ pulls in ~100 Rust crates and Python deps — real supply-chain
  surface. Mitigated by `cargo audit` + `pip-audit` in CI.

## Alternatives Considered

- **Skip nautilus, keep Python forever.** Loses "same code" guarantee. If we
  outgrow retail scale (>10 concurrent strategies, sub-second decisions),
  we'd have to rewrite everything.
- **Adopt Lean.** More mature Indian ecosystem support in community, but
  weaker same-code guarantee and C# is not a language we want to maintain.
- **Wait for someone to publish a nautilus-kite adapter.** No signal anyone is
  building one.

## Follow-ups

- Verify autobahn compatibility with kiteconnect after we forced the upgrade
  (see ADR-0005).
- Write ADR-0004 for iTrader adapter port specifics.
