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
