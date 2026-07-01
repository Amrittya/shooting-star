# ADR-0003 — LLM agents produce artifacts, not commands; never in order-placement hot path

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Amrittya, Claude

## Context

The predecessor project (iTrader) placed an LLM in the strategy-decision loop:
`StrategyAgent.generate_signals()` called Claude per bar, per symbol, to
decide BUY/SELL/HOLD. Analysis of that architecture showed the pattern is
wasteful (1-3 sec/call, ~$250/year at 100 cycles/day), fragile (LLM API
downtime halts trading), and adds latency variance to what should be a
deterministic hot path.

The published trading-agent literature (TradingAgents arXiv:2412.20138 et al.)
shows favorable numbers on curated backtests, but no evidence of live-trading
success at retail scale. Multi-agent LLM decisioning in the order-placement
loop is not proven.

## Decision

**Agents produce artifacts, not commands.** Specifically:

- **L1 (news_event, regime_narrator):** structured Pydantic outputs
  (`EventTag`, `RegimeTag`) written to the artifact store. Strategies consume
  via `ctx.features` / `ctx.on_event()` / `ctx.on_regime_change()`.
- **L2 (strategy_rd):** proposes strategy code. **Human reviews before
  deploy.** Auto-deploy is permitted only to paper mode, never live.
- **L3 (post-trade + risk monitor):** read-only. Nightly analyst reports,
  weekly reflection over structured telemetry, intraday anomaly alerts.
  Never modifies positions or configuration.

**Explicit non-goal:** no LLM call in the order-placement hot path. Ever.
The strategy engine reads `ctx.features.*` (deterministic, cached artifacts)
and applies rule-based logic. If an artifact is stale or missing, the engine
falls back to a safe default; it does not block waiting for an LLM call.

**Reflection cadence:** weekly minimum on structured telemetry. Not nightly
on individual trade outcomes — that's overfitting to noise.

## Consequences

**Positive:**
- Deterministic latency on the hot path (~ms, not seconds).
- LLM API outage cannot halt trading; only degrades the freshness of feature
  artifacts.
- Every LLM call is logged with prompt + response + cost + model version for
  post-hoc audit.
- Budget cap is enforceable (see `ti_agents/shared/budget.py`).

**Negative:**
- Agents cannot "react" to intraday events with sub-minute latency. Acceptable
  because our strategies are bar-based (1-min+), not tick-based.
- More discipline required in strategy code — agents don't decide, strategies
  do. This is the correct division of labor.

## Alternatives Considered

- **LLM in decision loop.** Rejected per iTrader post-mortem: cost, latency,
  fragility, and no evidence of alpha.
- **Fully deterministic system, no LLMs.** Loses the genuinely useful research
  and post-trade analysis capabilities that LLMs handle well.
- **Auto-deploy L2-generated code to live.** Rejected as unsafe; the code review
  gate is a hard requirement.

## Follow-ups

- Define the artifact schema in `ti_agents/shared/artifacts.py`.
- Implement `ti_agents/shared/budget.py` before any L2 agent runs (Phase 5+).
