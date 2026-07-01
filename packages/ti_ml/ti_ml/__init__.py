"""Classical ML for Shooting Star.

- Meta-labeling (López de Prado triple-barrier) — used as signal FILTER, not price predictor.
- Regime classification — RegimeClassifier protocol with 3 impls: HMM, change-point, clustering.
- Vol forecasting — HAR-RV (Corsi 2009) primary; GARCH sanity-check baseline only.

No deep learning in v1 by policy (LSTM/transformer vol models routinely disappear
when HAR baseline is included honestly and transaction costs are applied).
"""

__version__ = "0.1.0"
