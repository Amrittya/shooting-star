# Architecture Decision Records

This directory captures material architectural decisions for Shooting Star.
Each ADR follows a lightweight format: **Context**, **Decision**, **Consequences**.

Numbered chronologically; superseded ADRs stay in place with a link forward.

## Index

- [ADR-0001](adr-0001-nautilus-with-interim-pykite.md) — Nautilus-trader as long-term core; interim PykiteBroker in Python.
- [ADR-0002](adr-0002-regulatory-regime-overlay.md) — Regulatory-regime overlay for backtests (SEBI Oct-2024 + Budget-2026).
- [ADR-0003](adr-0003-agents-out-of-band.md) — LLM agents produce artifacts, not commands; never in order-placement hot path.
- [ADR-0004](adr-0004-port-itrader-adapter.md) — Port iTrader ZerodhaBroker as interim `PykiteBroker`, with specific fixes.
- [ADR-0005](adr-0005-vuln-overrides.md) — Override vulnerable transitive deps (autobahn PYSEC-2020-25).
