"""LLM / agentic layer for Shooting Star.

Design principle: agents produce ARTIFACTS (event tags, regime tags, reports,
code proposals), not COMMANDS. The deterministic strategy engine consumes
artifacts via ctx.features / ctx.on_event() / ctx.on_regime_change().
No LLM call is ever in the order-placement hot path.

Agent tiers:
- L1 (news_event, regime): out-of-band, low-latency, structured outputs.
- L2 (strategy_rd): human-in-loop code approval; auto-deploy to paper only.
- L3 (monitor): read-only post-trade analyst + intraday anomaly watcher.
"""

__version__ = "0.1.0"
