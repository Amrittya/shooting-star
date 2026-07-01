"""Data ingestion, storage, and serving for Shooting Star.

Storage layout:
- OHLCV bars: Parquet partitioned by (exchange, symbol, year, month), DuckDB views on top.
- Ticks (captured live): Parquet partitioned by (date, symbol).
- Option chain snapshots: Parquet partitioned by (date, underlying).
- Metadata (instruments, trades, runs): SQLite (portable to Postgres later).
- Feature store: Parquet, keyed by (timestamp, symbol).
"""

__version__ = "0.1.0"
