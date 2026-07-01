//! nautilus-kite — Zerodha Kite Connect adapter for nautilus-trader.
//!
//! This crate is a placeholder for the Phase 4 Rust adapter. It will
//! eventually implement:
//! - `InstrumentProvider` (NSE + NFO + BFO segment loading)
//! - `LiveMarketDataClient` (KiteTicker WebSocket subscription)
//! - `LiveExecutionClient` (order submit/modify/cancel, reconciliation)
//!
//! For v1, the interim Python `PykiteBroker` in `packages/ti_execution/`
//! (ported from iTrader) provides the same interface. When this crate
//! is production-ready, strategies swap to it with zero code changes.

#![deny(unsafe_op_in_unsafe_fn)]
#![warn(clippy::all, clippy::pedantic)]
#![allow(clippy::missing_errors_doc, clippy::module_name_repetitions)]

/// Placeholder — real modules land in Phase 4.
pub const CRATE_VERSION: &str = env!("CARGO_PKG_VERSION");

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn crate_version_is_set() {
        assert!(!CRATE_VERSION.is_empty());
    }
}
