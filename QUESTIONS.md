# Questions for Amrittya

*Overnight worklog: Claude ran autonomously starting 2 Jul 2026 ~22:00 IST. This file captures every question or ambiguity I hit while you were asleep. Review in the morning; each item is triaged as P0 (blocks progress) / P1 (needs decision within a week) / P2 (nice-to-have clarification).*

---

## P0 — Blocked, needs your call

*(none yet — will populate as I hit real blockers)*

---

## P1 — Needs decision this week

*(none yet)*

---

## P2 — Nice-to-have clarification

### Git author identity

I set the local git author to `Amrittya <amrittya.aakash.aswal@sap.com>` matching the iTrader repo. If you'd rather use a different identity (personal email, GitHub noreply) for a private trading project, run:

```bash
cd shooting-star
git config user.email "<preferred-email>"
```

I did NOT set up any GitHub remote. Local-only per your instruction.

### Python version

Local `python3` is 3.11.14. I pinned `pyproject.toml` to `requires-python = ">=3.11,<3.13"` — Python 3.13 has some numpy/pandas ABI churn I want to avoid. If you want to run on 3.12+ specifically, tell me.

### `uv` version

Local `uv` is 0.10.0 (Feb 2026). Current release is 0.11.26 (Jun 2026). I did not upgrade globally — could affect your other projects. Upgrade with `brew upgrade uv` when convenient.

---

## Design ambiguities I resolved by educated guess

*(I'll add to this list as they arise. Each entry documents the ambiguity, my guess, and my reasoning — so you can override in the morning if the guess is wrong.)*

### None yet.

---

*Last updated: (will be updated after each commit)*
