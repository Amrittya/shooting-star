# Overnight worklog — 2 Jul 2026

*This file is Claude's running log during the autonomous overnight build.
Sections are appended incrementally; each phase ends with a git commit that
you can review with `git log --oneline` and `git show <hash>`.*

## Ground rules I set for myself

- Every commit is atomic and passes CI on its own.
- No live broker API calls; no real credentials touched.
- No `pip install` outside pinned `pyproject.toml`.
- No `git push`, no destructive git ops.
- Any real ambiguity → `QUESTIONS.md`, no guessing.
- Research freely; verify library versions before pinning.

## Verified versions at start of night (2 Jul 2026)

- Python 3.11.14 (local)
- uv 0.10.0 (local; latest is 0.11.26 — did not upgrade globally)
- ruff 0.15.20 (latest, pinned)
- mypy 2.1.0 (latest, pinned)
- pytest 9.1.1 (latest, pinned)
- structlog 26.1.0 (latest, pinned)
- pydantic 2.13.4 (latest, pinned)
- duckdb 1.5.4 (latest, pinned)
- pykiteconnect 5.2.0 (latest, pinned)
- nautilus-trader 1.230.0 (latest, pinned)
- Docker 29.1.3 / Compose v5.0.0
- Rust 1.95.0 / Cargo 1.95.0

## Phase 0.1 — Repo scaffold (completed ~22:35 IST, commit 9f8c2ad)

**Files created:**
- `.gitignore` (Python + data + IDE + secrets)
- `.env.example` (all env vars documented; NO real secrets)
- `README.md` (top-level project overview)
- `QUESTIONS.md` (running list of ambiguities for Amrittya)
- `pyproject.toml` (uv workspace root, ruff+mypy+pytest+coverage config)
- 10× `packages/ti_*/pyproject.toml` + `__init__.py` + `py.typed`
- `docker-compose.yml` (Redis mandatory, Postgres opt-in via profile)
- `Cargo.toml` (Rust workspace root)
- `rust/nautilus-kite/{Cargo.toml,src/lib.rs}` (placeholder)

**Correction mid-flight:**
- kiteconnect PyPI name (not pykiteconnect)
- Python 3.11 dropped by numpy 2.5 / xgboost 3.3 — bumped to 3.12+
- 8 library version guesses corrected against real PyPI data

**Decisions logged:**
- Python 3.12-3.13. Not 3.14 yet.
- SQLite for v1 metadata; Postgres available via docker-compose profile.
- Rust workspace exists but Phase 4 (weeks 4-16 in plan).
- Redis bound to localhost only — never externally exposed.

**CI gates verified green:** ruff, ruff-format, mypy strict, pytest (0 tests).

## Phase 0.2 — CI + tooling (started ~22:40 IST)

- `.pre-commit-config.yaml` (ruff, mypy, gitleaks, standard hooks)
- `Makefile` (help, sync, lint, fmt, type, test, cov, audit, ci, clean, docker-*)
- `.github/workflows/ci.yml` (documents CI contract; runs when remote is added)
- `packages/ti_core/tests/test_imports.py` — sanity import test for all 10 packages

**Real finding: PYSEC-2020-25 in autobahn 19.11.2** (pinned by kiteconnect 5.2.0).
Forced override to autobahn ≥22.7.1 (resolved 26.6.2). Documented in ADR-0005.
Risk logged to QUESTIONS.md: kiteconnect may not work with autobahn 26; needs
runtime verification against Kite paper mode.

**CI gates green:** ruff, ruff-format, mypy strict, pytest (10 tests), pip-audit.

## Phase 0.4 — ADRs (pulled forward, completed with 0.2)

- ADR-0001: Nautilus-trader + interim PykiteBroker
- ADR-0002: Regulatory-regime overlay (SEBI dates confirmed against circular)
- ADR-0003: Agents out-of-band, never in hot path
- ADR-0004: Port iTrader adapter with specific fixes
- ADR-0005: autobahn vulnerability override

**Next:** commit Phase 0.2 + 0.4 together, then Phase 0.3 (ti_core: config, logging, clock, events).

## Phase 0.3 — ti_core (completed ~23:15 IST)

**Modules written:**
- `config.py` — Pydantic `Settings` loaded from env, validated at construction.
  Kill-switch percentages / capital / greek limits all bounds-checked at load.
  Secrets wrapped in `SecretStr`. `require_broker()` and `require_llm()`
  guards for fail-fast startup in paper/live modes. Singleton via
  `get_settings()`.
- `clock.py` — `Clock` abstract + `SystemClock` (wall) + `ManualClock`
  (backtest). UTC internally, IST at display boundaries. `is_market_open()`
  checks NSE regular session (09:15–15:30 IST, weekdays only, no holiday
  awareness yet — that lives in `ti_data`).
- `logging.py` — structlog config, JSON default. Secret redaction processor
  runs BEFORE any renderer: catches SecretStr values and any dict key matching
  a broad regex (api_key, access_token, password, kite_api, anthropic_api,
  etc). Shallow-recurses one level into nested contexts.
- `events.py` — `EventBus` abstract + `InMemoryEventBus`. Type-driven
  subscription (subscribe to `type[Event]`, not channel string). Fan-out
  runs handlers concurrently; exceptions propagate after all handlers ran.

**Tests: 62 passing, 95% coverage on ti_core.**

- test_config: defaults, env overrides, SecretStr wrapping, validator bounds
  (kill %, positive capital), `require_broker`/`require_llm` guards.
- test_clock: UTC awareness, IST conversion, `is_market_open` boundary
  conditions, ManualClock forward-only advance, tz-aware assertion.
- test_logging: pattern matches for secret key names, redaction of SecretStr,
  nested-dict redaction, JSON output structure, idempotent configure_logging.
- test_events: subscribe/publish, multiple handlers, type-driven routing
  (OrderPlaced vs OrderFilled isolation), empty-fan-out no-op,
  handler-exception-propagates-after-fanout, close clears state.

**Bugs I caught in my own code by running tests:**
- structlog `cache_logger_on_first_use=True` meant handler swaps between
  tests were ignored → test rewrite to use `capsys` + `structlog.reset_defaults()`.
- TC003 (type-checking imports) required `Path` to move into TYPE_CHECKING
  blocks in three files.
- Two mypy strict issues (wrong type: ignore code, unannotated Any return
  from `structlog.get_logger`).

**Next:** commit Phase 0.3, then Phase 1.1 (ti_data storage + bias guards).

## Phase 1.1 — ti_data storage + bias guards (completed ~23:55 IST)

**Modules written:**
- `ti_data/storage/schema.py` — SQLAlchemy 2.0 declarative models for
  metadata.db. Five tables:
  - `instruments` — point-in-time (valid_from/valid_to) with unique
    constraint on (instrument_token, valid_from). Supports SEBI lot-size
    rebalances by design.
  - `runs` — one row per backtest/paper/live session, config_hash for
    reproducibility.
  - `trades` — closed trades, gross/charges/net PnL, `regulatory_regime`
    field for ADR-0002 overlay.
  - `kill_switch_state` — persistent per-(scope, level) kill switches.
  - `agent_artifacts` — L1/L2/L3 outputs with LLM audit info (model,
    tokens, cost).
- `ti_data/bias_guards.py` — the linchpin invariant enforcement:
  - `assert_no_lookahead` — every bar-shaped frame passing to strategy
    code must have `bar_close_time <= clock.now() + slack`. Slack is 0
    in backtest, small positive in live/paper.
  - `assert_instrument_query_is_point_in_time` — raw SQL touching the
    `instruments` table must filter on both valid_from AND valid_to.
    Defense-in-depth for the few places raw SQL is used.
  - Both raise AssertionError subclasses (LookAheadError,
    SurvivorshipError) so they cannot be caught by generic `except Exception`.

**Tests: 21 (14 bias guards, 7 schema). Total repo: 83 passing.**

- Bias-guard tests: past/present/future frames, slack behavior, empty
  frame, missing column, forward-clock-advance, and full survivorship
  matrix (missing valid_from, missing valid_to, both missing, correct
  form, non-instrument queries).
- Schema tests: PIT snapshot storage (two rows for same tradingsymbol
  with different lot sizes), unique constraint enforcement, Run↔Trade
  relationship, kill-switch scope/level uniqueness, agent artifact
  LLM audit fields.

**Pytest infrastructure fix:** enabled `--import-mode=importlib` in
pytest config so multiple `packages/*/tests/` directories don't collide
on the shared `tests` module name.

**Next:** Phase 1.2 was scoped but this session is running long. Committing
Phase 1.1 and setting Phase 1.2 aside for the morning. See summary in the
final commit.

## End-of-session summary (~00:15 IST, 3 Jul 2026)

### What got done tonight (4 atomic commits)

- **Phase 0.1** (9f8c2ad): repo scaffold, 10-package uv workspace,
  docker-compose, Rust workspace placeholder.
- **Phase 0.2 + 0.4** (16478f5): CI tooling (Makefile, pre-commit,
  GitHub Actions), 5 ADRs, autobahn vulnerability override.
- **Phase 0.3** (76bc2fd): ti_core — config (Pydantic Settings), clock
  (System/Manual), logging (structlog with secret redaction), events
  (typed in-memory bus).
- **Phase 1.1** (9362f4e): ti_data — SQLAlchemy schema (Instrument PIT,
  Run, Trade with regulatory_regime, KillSwitchState, AgentArtifact) +
  bias guards (look-ahead + survivorship, both raise AssertionError
  subclasses).

### Metrics

- **83 Python tests passing.** 96% coverage on the code that has tests.
  (Coverage gaps are in un-exercised branches, not untested modules.)
- **1 Rust test passing.** Workspace crate builds clean.
- **mypy strict:** 18 files, 0 issues.
- **ruff:** 26 files, 0 issues.
- **pip-audit:** no known vulnerabilities (after autobahn override).

### What did NOT get done

- **Phase 1.2** (Kite historical ingestor, even mocked). Deliberately
  deferred — proper implementation with rate-limit queue and
  point-in-time instrument snapshotting is a full day's work; a rushed
  version overnight would create rework.
- **Phase 2** (port iTrader ZerodhaBroker with fixes). Same reasoning
  — this is where the highest-value work lives and it deserves a full
  focused session, not the last hour of a long night.

### For morning-Amrittya

1. Read `QUESTIONS.md` first. One P1 item (autobahn compat) needs
   runtime verification before any Kite integration testing.
2. Read `docs/adr/` to understand the design commits I made on your
   behalf (5 ADRs).
3. Read `docs/OVERNIGHT_WORKLOG.md` (this file) for the running
   commentary on decisions and corrections.
4. Try `make ci` — everything should be green.
5. Try `make docker-up` and confirm Redis is happy.
6. If any of the above misbehaves, `git log` shows atomic commits you
   can revert individually.
