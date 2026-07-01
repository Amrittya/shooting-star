"""Deterministic risk engine — sits in the order-placement hot path.

Every order intent passes through pre-trade checks:
kill-switch state -> capital -> greeks -> margin (Kite /margins/basket)
-> charges -> position limits -> freeze qty -> tradability -> expiry-day rules
-> event blackout.
"""

__version__ = "0.1.0"
