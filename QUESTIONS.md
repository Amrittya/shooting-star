# Questions for Amrittya

*Overnight worklog: Claude ran autonomously starting 2 Jul 2026 ~22:00 IST. This file captures every question or ambiguity I hit while you were asleep. Review in the morning; each item is triaged as P0 (blocks progress) / P1 (needs decision within a week) / P2 (nice-to-have clarification).*

---

## P0 — Blocked, needs your call

*(none yet — will populate as I hit real blockers)*

---

## P1 — Needs decision this week

### 1. autobahn version override may break Kite WebSocket

`kiteconnect 5.2.0` pins `autobahn[twisted]==19.11.2`, which has PYSEC-2020-25.
I forced an override to `autobahn>=22.7.1` (resolved to 26.6.2) to clear the
vulnerability. See `docs/adr/adr-0005-vuln-overrides.md`.

**The risk:** kiteconnect's `KiteTicker` (WebSocket) may not work correctly
with autobahn 26. autobahn 20+ changed some handshake APIs. I have NO way to
integration-test this without a live Kite session, which I refuse to do while
you're asleep.

**Action needed from you in the morning:**
1. When you first run `PykiteBroker` against Kite paper mode, watch for
   WebSocket connection errors.
2. If it breaks, decide: (a) revert to autobahn 19.11.2 and accept the CVE
   as a known-issue-with-compensating-controls, or (b) fork kiteconnect and
   unpin autobahn ourselves.
3. Report back so I can update ADR-0005 with the resolution.

---

## P2 — Nice-to-have clarification

### 2. Python version bumped to 3.12+

Original plan targeted Python 3.11+. Numpy 2.5 and xgboost 3.3 both dropped
Python 3.11 support (they now require 3.12+). To use current ML tooling, I
bumped `requires-python = ">=3.12,<3.14"`.

You have `python3.13` (3.13.12) installed locally, so this works. `uv sync`
will use 3.13 by default. If you want to target 3.12 specifically:
`uv python pin 3.12`.

### 3. Git author identity

I set the local git author to `Amrittya <amrittya.aakash.aswal@sap.com>` matching the iTrader repo. If you'd rather use a different identity (personal email, GitHub noreply) for a private trading project, run:

```bash
cd shooting-star
git config user.email "<preferred-email>"
```

I did NOT set up any GitHub remote. Local-only per your instruction.

### 4. `uv` version

Local `uv` is 0.10.0 (Feb 2026). Current release is 0.11.26 (Jun 2026). I did not upgrade globally — could affect your other projects. Upgrade with `brew upgrade uv` when convenient.

---

## Design ambiguities I resolved by educated guess

*(I'll add to this list as they arise. Each entry documents the ambiguity, my guess, and my reasoning — so you can override in the morning if the guess is wrong.)*

### None yet.

---

*Last updated: (will be updated after each commit)*
