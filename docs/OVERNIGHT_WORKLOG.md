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

## Phase 0.1 — Repo scaffold (started ~22:15 IST)

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

**Decisions logged:**
- Python 3.11-3.12 only. Not 3.13 yet (numpy/pandas ABI churn).
- SQLite for v1 metadata; Postgres available via docker-compose profile.
- Rust workspace exists but Phase 4 (weeks 4-16 in plan).
- Redis bound to localhost only — never externally exposed.

**Next:** commit Phase 0.1, then Phase 0.2 (CI tooling verification + pre-commit).
