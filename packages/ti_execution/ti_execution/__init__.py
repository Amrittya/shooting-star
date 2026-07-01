"""Order routing and broker adapters.

Two adapter implementations behind a single BrokerAdapter interface:
- PykiteBroker: pure-Python via pykiteconnect (paper trading + interim live).
- (future) NautilusKiteBroker: Rust adapter for nautilus-trader (production).

Strategies target the interface, not the concrete adapter, so we can swap
without touching strategy code.
"""

__version__ = "0.1.0"
