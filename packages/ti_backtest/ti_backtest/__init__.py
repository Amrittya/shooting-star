"""Backtesting engine and rigor layer.

Nautilus-trader is the target event-driven engine; this package adds:
- Walk-forward orchestration (anchored + rolling)
- Monte Carlo trade-sequence resampling
- Bias guards (look-ahead, survivorship)
- Regulatory-regime overlay (SEBI Oct-2024 + Budget-2026 boundaries)
- Tick-calibrated slippage models
- VectorBT bridge for entry-signal parameter sweeps
"""

__version__ = "0.1.0"
