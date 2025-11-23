# ecosystem/network_state.py
"""
network_state.py — XRPL network snapshot helper for the Governor lab.

This module is deliberately defensive and self-healing:
- It *tries* to use xrpl_rpc if available.
- If no suitable helper exists, it falls back to a safe local default.
- It always returns a normalized dict used by flow_engine, multileg, sdk, etc.
"""

from typing import Any, Dict

try:
    import xrpl_rpc  # type: ignore[import]
except ImportError:  # running totally offline / no rpc module
    xrpl_rpc = None  # type: ignore[assignment]


def _default_snapshot() -> Dict[str, Any]:
    """
    Local, safe default snapshot when xrpl_rpc can't help.

    These numbers match the style used elsewhere in your stack:
      median_fee ≈ 5000 drops
      recommended_fee ≈ 5000 drops
      safe_fee = recommended + 500
    """
    return {
        "ledger_seq": 0,
        "load_factor": 1.0,
        "txn_median_fee": 5000,
        "recommended_fee_drops": 5000,
        "safe_fee_drops": 5500,
        "txn_base_fee": 10,
    }


def _raw_fee_snapshot() -> Dict[str, Any]:
    """
    Try multiple helper names on xrpl_rpc so we don't depend
    on one exact function name. If nothing is found, fall back
    to the local default snapshot.
    """
    if xrpl_rpc is None:
        # No rpc module at all – just use defaults
        return _default_snapshot()

    # Preferred modern name
    if hasattr(xrpl_rpc, "get_fee_snapshot"):
        snap = xrpl_rpc.get_fee_snapshot()  # type: ignore[attr-defined]
        if isinstance(snap, dict):
            return snap

    # Common alternates in XRPL client code
    if hasattr(xrpl_rpc, "get_fee"):
        snap = xrpl_rpc.get_fee()  # type: ignore[attr-defined]
        if isinstance(snap, dict):
            return snap

    if hasattr(xrpl_rpc, "get_fees"):
        snap = xrpl_rpc.get_fees()  # type: ignore[attr-defined]
        if isinstance(snap, dict):
            return snap

    if hasattr(xrpl_rpc, "get_fee_and_ledger"):
        snap = xrpl_rpc.get_fee_and_ledger()  # type: ignore[attr-defined]
        if isinstance(snap, dict):
            return snap

    # If we reach here, xrpl_rpc exists but doesn't expose any of
    # the helpers we know how to use. Rather than exploding, we
    # return a sane local default.
    return _default_snapshot()


def get_network_state() -> Dict[str, Any]:
    """
    Return a normalized network_state dict:

        {
            "ledger_seq": int,
            "load_factor": float,
            "txn_median_fee": int,
            "recommended_fee_drops": int,
            "safe_fee_drops": int,
            "txn_base_fee": int,
        }

    All callers use this shape instead of touching xrpl_rpc directly.
    """
    snap = _raw_fee_snapshot()

    ledger_seq = (
        snap.get("ledger_current_index")
        or snap.get("ledger_index")
        or snap.get("ledger_seq")
        or 0
    )

    load_factor = float(snap.get("load_factor", 1.0))

    median_fee = int(
        snap.get(
            "txn_median_fee",
            snap.get("median_fee", snap.get("base_fee", 10)),
        )
    )

    recommended = int(snap.get("recommended_fee_drops", median_fee))
    base_fee = int(snap.get("txn_base_fee", snap.get("base_fee", 10)))

    # Ensure safe_fee is always >= recommended
    safe_fee = max(recommended, median_fee) + 500

    return {
        "ledger_seq": ledger_seq,
            "load_factor": load_factor,
        "txn_median_fee": median_fee,
        "recommended_fee_drops": recommended,
        "safe_fee_drops": safe_fee,
        "txn_base_fee": base_fee,
    }
