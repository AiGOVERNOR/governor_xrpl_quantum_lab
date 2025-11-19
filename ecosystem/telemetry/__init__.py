"""
Telemetry utilities for the VQM Ecosystem.

This module is intentionally lightweight and defensive:
- No network I/O.
- No hard dependencies on XRPL internals.
- All helpers accept plain dicts/lists and return plain dicts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------
# Fee band classification
# ---------------------


@dataclass
class FeeBand:
    band: str
    comment: str


def classify_fee_band(median_fee_drops: int, load_factor: float) -> Dict[str, Any]:
    """
    Classify median fee + load_factor into human-readable fee bands.

    This is intentionally simple and conservative. You can tune thresholds later.

    Returns:
        {
          "band": "low" | "normal" | "elevated" | "extreme",
          "comment": str
        }
    """
    if median_fee_drops <= 15 and load_factor <= 1.5:
        band = "low"
        comment = "Plenty of capacity. Fees are very low."
    elif median_fee_drops <= 50 and load_factor <= 2.0:
        band = "normal"
        comment = "Network healthy. Standard fees."
    elif median_fee_drops <= 2000 or load_factor <= 4.0:
        band = "elevated"
        comment = "Fee pressure rising; consider prioritizing essential flows."
    else:
        band = "extreme"
        comment = "Severe congestion / fee pressure. Only essential flows should be active."

    return {
        "band": band,
        "comment": comment,
    }


# ---------------------
# Ledger rate estimation
# ---------------------


def compute_ledger_rate(history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, float]:
    """
    Compute a rough ledger close rate from an optional history buffer.

    For now, this is intentionally forgiving:
    - If history is missing/short/bad → fall back to XRPL's expected 3-5s per ledger.
    - No exceptions, no hard failures.

    Returns:
        {
          "ledgers_per_second": float,
          "seconds_per_ledger": float,
        }
    """
    # Conservative default for safety.
    DEFAULT_SECONDS_PER_LEDGER = 4.0

    if not history or len(history) < 2:
        return {
            "ledgers_per_second": 1.0 / DEFAULT_SECONDS_PER_LEDGER,
            "seconds_per_ledger": DEFAULT_SECONDS_PER_LEDGER,
        }

    # Best-effort: try to compute from first/last timestamps if present.
    try:
        # Expect something like:
        # [{"ledger_seq": 100, "timestamp": 1731990000.0}, ...]
        first = history[0]
        last = history[-1]

        l0 = int(first.get("ledger_seq") or first.get("ledger_index"))
        l1 = int(last.get("ledger_seq") or last.get("ledger_index"))

        t0 = float(first.get("timestamp") or first.get("ts"))
        t1 = float(last.get("timestamp") or last.get("ts"))

        if t1 <= t0 or l1 <= l0:
            raise ValueError("non-increasing ledger/time")

        delta_ledgers = float(l1 - l0)
        delta_time = float(t1 - t0)

        lps = delta_ledgers / delta_time
        spl = delta_time / delta_ledgers

        return {
            "ledgers_per_second": lps,
            "seconds_per_ledger": spl,
        }
    except Exception:
        # Never let telemetry math break the pipeline.
        return {
            "ledgers_per_second": 1.0 / DEFAULT_SECONDS_PER_LEDGER,
            "seconds_per_ledger": DEFAULT_SECONDS_PER_LEDGER,
        }


# ---------------------
# Guardian Attestation
# ---------------------


def make_guardian_attestation(
    network_state: Dict[str, Any],
    mode: str,
    recommended_fee: int,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a compact attestation record for Guardian / audit logs.

    Args:
        network_state: dict with fields like ledger_seq, txn_median_fee, load_factor, etc.
        mode: current operating mode ("normal", "fee_pressure", etc.).
        recommended_fee: the fee (drops) that policies are converging on.
        extra: optional dict of additional context.

    Returns:
        dict suitable for logging / JSON export.
    """
    base = {
        "mode": mode,
        "recommended_fee": recommended_fee,
        "network_state": {
            "ledger_seq": network_state.get("ledger_seq"),
            "txn_median_fee": network_state.get("txn_median_fee"),
            "txn_base_fee": network_state.get("txn_base_fee"),
            "recommended_fee_drops": network_state.get("recommended_fee_drops"),
            "load_factor": network_state.get("load_factor"),
        },
    }
    if extra:
        base["extra"] = extra
    return base
