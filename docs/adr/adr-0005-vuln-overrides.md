# ADR-0005 — Vulnerability overrides for pinned transitive dependencies

**Status:** Accepted
**Date:** 2026-07-02
**Deciders:** Amrittya, Claude

## Context

`kiteconnect 5.2.0` (the official Zerodha Kite Python client) pins
`autobahn[twisted]==19.11.2`. That version has a known vulnerability:

- **PYSEC-2020-25** (autobahn 19.11.2). Fixed in 20.12.3+.

`pip-audit` correctly flags this. We cannot upgrade `kiteconnect` because 5.2.0
is the latest release. Simply accepting the vulnerability would leave a
CVE-tagged dependency in a codebase that handles broker credentials.

## Decision

**Force-override the transitive `autobahn` pin via `[tool.uv]
override-dependencies` in the root `pyproject.toml`:**

```toml
[tool.uv]
override-dependencies = [
    "autobahn>=22.7.1",
]
```

uv resolves this to autobahn 26.6.2 as of 2026-07-02, which patches
PYSEC-2020-25 and all subsequent CVEs.

## Consequences

**Positive:**
- No known vulnerabilities in the dependency tree.
- Override is declarative and versioned in the pyproject.toml (visible to
  reviewers, not hidden in a lockfile hack).

**Negative:**
- **Kite may break at runtime.** kiteconnect pinned 19.11.2 for a reason;
  autobahn 20+ changed some WebSocket handshake APIs. The Python `KiteTicker`
  class uses autobahn for its WebSocket implementation. We do NOT have
  integration test coverage against a live Kite session in this repo.
- **Mitigation:** the interim `PykiteBroker` (Phase 2) will be unit-tested
  against a mocked KiteConnect client. Any autobahn incompatibility surfaces
  when Amrittya runs it against a live Kite paper session for the first time.
  If it breaks, fallback plan: pin autobahn back to 19.11.2 and mitigate
  the vulnerability by (a) never exposing the KiteTicker WebSocket to
  untrusted network paths (it's localhost-to-Zerodha only), (b) tracking
  https://kite.trade for a kiteconnect release that lifts the pin.

## Alternatives Considered

- **Accept the vulnerability.** Rejected — this is a trading system with
  broker credentials; the risk-benefit is wrong.
- **Fork kiteconnect and unpin autobahn.** Rejected — maintenance burden.
- **Replace kiteconnect entirely with our own Kite HTTP+WS client.**
  Reasonable long-term option; that's exactly what the Rust nautilus-kite
  adapter is (Phase 4). Interim, we live with the override.

## Follow-ups

- **Amrittya must integration-test `PykiteBroker` against Kite paper mode
  before promoting anything to live.** If autobahn 26 breaks Kite WebSocket,
  revert the override and add PYSEC-2020-25 to the audit ignore list with
  a compensating-control note.
- Watch for kiteconnect 5.3+ that lifts the autobahn pin. Remove this
  override when it lands.
