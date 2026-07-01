# Shooting Star

Personal, semi-autonomous trading intelligence engine for Indian markets (NSE/BSE), targeting NIFTY/BANKNIFTY index options + cash equities on Zerodha.

> The project is named after the reversal candlestick pattern — apt for a system whose whole purpose is to know when the tape is about to turn.

**Status:** Phase 0 scaffold. See `docs/OVERNIGHT_WORKLOG.md` for the incremental build log; see `/Users/i543879/.claude/plans/cryptic-hopping-lamport.md` for the full design plan.

## What this is

Shooting Star is a monorepo with the following packages:

- `ti_core` — shared domain types, config, logging, event bus.
- `ti_data` — ingestion, storage (Parquet + DuckDB + SQLite), serving.
- `ti_strategy` — strategy framework + concrete strategies (option selling, option buying, equity).
- `ti_analysis` — technical/fundamental analysis, options greeks, IV surface features.
- `ti_backtest` — nautilus-based backtesting with walk-forward, Monte Carlo, bias guards.
- `ti_risk` — deterministic risk engine (pre-trade checks, charges model, kill switches, stress).
- `ti_execution` — order routing, retry, reconciliation. Contains interim `pykit_broker` (ported from iTrader) until the Rust nautilus adapter is production-ready.
- `ti_ml` — meta-labeling, regime classification (HMM / change-point / clustering), HAR-RV vol forecasting.
- `ti_agents` — L1/L2/L3 out-of-band agents (news/event, regime narrator, strategy R&D, post-trade monitor). Never in the order-placement hot path.
- `ti_ui` — CLI (typer) + FastAPI dashboard.

Plus a Rust workspace at `rust/nautilus-kite/` for the eventual nautilus-trader adapter.

## Key design principles

1. **Same code runs backtest = paper = live.** Nautilus-trader is the target execution core.
2. **LLMs produce artifacts, not commands.** Agents are out-of-band; deterministic engine handles orders.
3. **ML is a filter (meta-labeling) or classifier (regime), never a price predictor.**
4. **Backtest-to-live gap is the #1 risk.** Bias guards, captured-tick slippage, walk-forward + Monte Carlo mandatory.
5. **Regulatory-regime aware.** Charges model is date-parameterized (SEBI Oct-2024 + Budget-2026 boundaries baked in).

## Getting started

Requires: Python 3.11+, `uv`, Docker, `docker compose`, Rust toolchain (for the Rust adapter track).

```bash
# 1. Clone and enter
cd shooting-star

# 2. Copy env template and fill in (leave broker keys blank for dev mode)
cp .env.example .env

# 3. Install deps into a uv workspace
uv sync

# 4. Run all quality gates
uv run ruff check .
uv run mypy .
uv run pytest

# 5. Start local infra (Redis for event bus)
docker compose up -d

# 6. Run the CLI (once Phase 2 lands)
uv run shooting-star --help
```

## Non-goals (v1)

- Single-stock options
- BankNifty / FinNifty / MidcpNifty weekly options (discontinued by SEBI Nov 2024)
- Cloud deployment
- HFT / sub-second strategies
- LLM in order-placement hot path
- Autonomous modification of live strategies
- Reinforcement learning
- SVI/SABR vol surface modeling
- SPAN margin reimplementation (use Kite `/margins/basket`)

## Repository layout

See `docs/ARCHITECTURE.md` (once written) and the master plan doc referenced above.

## License

Private. Not open source.
