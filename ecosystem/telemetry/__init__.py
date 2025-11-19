"""
Telemetry helpers for the VQM + XRPL ecosystem.

This module is intentionally forgiving about function signatures so
older and newer callers (RPC layers, pipelines, etc.) keep working.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------
# Ledger rate utilities
# ---------------------------------------------------------------------


def _normalize_ledger_args(*args, **kwargs) -> Dict[str, float]:
    """
    Accept diverse call styles:

      1) compute_ledger_rate(prev_ledger, prev_ts, curr_ledger, curr_ts)
      2) compute_ledger_rate(prev_dict, curr_dict)
      3) compute_ledger_rate(history_list)  <-- NEW, fixes your crash
      4) compute_ledger_rate(kwargs)
    """

    # ------------------------------------------------------------------
    # NEW: history list mode, e.g. compute_ledger_rate(self._ledger_history)
    # ------------------------------------------------------------------
    if len(args) == 1 and isinstance(args[0], list):
        hist = args[0]

        # Not enough data → return "neutral" values
        if len(hist) < 2:
            return {
                "prev_ledger": None,
                "prev_ts": None,
                "curr_ledger": None,
                "curr_ts": None,
            }

        prev = hist[-2]
        curr = hist[-1]

        return {
            "prev_ledger": int(prev.get("ledger_seq")),
            "prev_ts": float(prev.get("timestamp")),
            "curr_ledger": int(curr.get("ledger_seq")),
            "curr_ts": float(curr.get("timestamp", time.time())),
        }

    # ------------------------------------------------------------------
    # Style 1: 4 positional args
    # ------------------------------------------------------------------
    if len(args) == 4:
        prev_ledger, prev_ts, curr_ledger, curr_ts = args
        return {
            "prev_ledger": int(prev_ledger),
            "prev_ts": float(prev_ts),
            "curr_ledger": int(curr_ledger),
            "curr_ts": float(curr_ts),
        }

    # ------------------------------------------------------------------
    # Style 2: prev, curr dicts or objects
    # ------------------------------------------------------------------
    if len(args) == 2:
        prev, curr = args

        def extract(obj, field):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get(field)
            return getattr(obj, field, None)

        return {
            "prev_ledger": extract(prev, "ledger_seq"),
            "prev_ts": extract(prev, "timestamp"),
            "curr_ledger": extract(curr, "ledger_seq"),
            "curr_ts": extract(curr, "timestamp") or time.time(),
        }

    # ------------------------------------------------------------------
    # Style 3: kwargs
    # ------------------------------------------------------------------
    curr_ledger = kwargs.get("curr_ledger")
    curr_ts = kwargs.get("curr_ts", time.time())

    return {
        "prev_ledger": kwargs.get("prev_ledger"),
        "prev_ts": kwargs.get("prev_ts"),
        "curr_ledger": curr_ledger,
        "curr_ts": curr_ts,
    }

    # Style 1: compute_ledger_rate(prev_ledger, prev_ts, curr_ledger, curr_ts)
    if len(args) == 4 and all(not isinstance(a, dict) for a in args):
        prev_ledger, prev_ts, curr_ledger, curr_ts = args
        return {
            "prev_ledger": int(prev_ledger) if prev_ledger is not None else None,
            "prev_ts": float(prev_ts) if prev_ts is not None else None,
            "curr_ledger": int(curr_ledger),
            "curr_ts": float(curr_ts),
        }

    # Style 2: compute_ledger_rate(previous, current) where they are dict-like
    # or objects with ledger_seq / timestamp attributes.
    if len(args) == 2:
        prev, curr = args
        prev_ledger = getattr(prev, "ledger_seq", None) if prev is not None else None
        prev_ts = getattr(prev, "timestamp", None) if prev is not None else None
        if isinstance(prev, dict):
            prev_ledger = prev.get("ledger_seq", prev_ledger)
            prev_ts = prev.get("timestamp", prev_ts)

        curr_ledger = getattr(curr, "ledger_seq", None)
        curr_ts = getattr(curr, "timestamp", None)
        if isinstance(curr, dict):
            curr_ledger = curr.get("ledger_seq", curr_ledger)
            curr_ts = curr.get("timestamp", curr_ts)

        if curr_ledger is None:
            raise ValueError("current ledger_seq is required for compute_ledger_rate")

        if curr_ts is None:
            curr_ts = time.time()

        return {
            "prev_ledger": int(prev_ledger) if prev_ledger is not None else None,
            "prev_ts": float(prev_ts) if prev_ts is not None else None,
            "curr_ledger": int(curr_ledger),
            "curr_ts": float(curr_ts),
        }

    # Style 3: all kwargs
    prev_ledger = kwargs.get("prev_ledger")
    prev_ts = kwargs.get("prev_ts")
    curr_ledger = kwargs.get("curr_ledger")
    curr_ts = kwargs.get("curr_ts", time.time())
    if curr_ledger is None:
        raise ValueError("curr_ledger is required for compute_ledger_rate(kwargs)")

    return {
        "prev_ledger": int(prev_ledger) if prev_ledger is not None else None,
        "prev_ts": float(prev_ts) if prev_ts is not None else None,
        "curr_ledger": int(curr_ledger),
        "curr_ts": float(curr_ts),
    }


def compute_ledger_rate(*args, **kwargs) -> Dict[str, Any]:
    """
    Compute approximate ledger close rate.

    Returns:
        {
          "ledgers_per_second": float,
          "seconds_per_ledger": float,
          "sample_size": int,
        }
    """

    norm = _normalize_ledger_args(*args, **kwargs)
    prev_ledger = norm["prev_ledger"]
    prev_ts = norm["prev_ts"]
    curr_ledger = norm["curr_ledger"]
    curr_ts = norm["curr_ts"]

    if prev_ledger is None or prev_ts is None:
        # Not enough history yet – return neutral defaults.
        return {
            "ledgers_per_second": 0.0,
            "seconds_per_ledger": 0.0,
            "sample_size": 0,
        }

    d_ledger = curr_ledger - prev_ledger
    d_time = max(curr_ts - prev_ts, 1e-6)

    lps = d_ledger / d_time
    spl = 1.0 / lps if lps > 0 else 0.0

    return {
        "ledgers_per_second": lps,
        "seconds_per_ledger": spl,
        "sample_size": int(d_ledger),
    }


# ---------------------------------------------------------------------
# Fee band classification
# ---------------------------------------------------------------------


def classify_fee_band(
    median_fee_drops: Optional[int] = None,
    load_factor: float = 1.0,
    median_fee: Optional[int] = None,
    **_: Any,
) -> Dict[str, Any]:
    """
    Classify current fee / load conditions into broad bands.

    Compatible with callers that pass:
        - classify_fee_band(median_fee_drops=..., load_factor=...)
        - classify_fee_band(median_fee=..., load_factor=...)
    """

    # Backwards compat: allow either name.
    median = median_fee_drops if median_fee_drops is not None else median_fee
    if median is None:
        median = 10

    median = int(median)

    # Simple banding logic; you can tune thresholds later.
    if load_factor <= 1.2 and median <= 20:
        band = "low"
        comment = "Fees are low; plenty of capacity."
    elif load_factor <= 2.0 and median <= 50:
        band = "normal"
        comment = "Network in normal operating range."
    elif load_factor <= 4.0 or median <= 200:
        band = "elevated"
        comment = "Elevated fees; consider optimization / throttling."
    else:
        band = "extreme"
        comment = "Extreme fee pressure; delay non-critical flows."

    return {
        "band": band,
        "comment": comment,
        "median_fee_drops": median,
        "load_factor": float(load_factor),
    }


# ---------------------------------------------------------------------
# Guardian attestation builder
# ---------------------------------------------------------------------


def make_guardian_attestation(network_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight attestation blob for Guardian / VQM pipelines.

    Input is expected to look like:
        {
          "ledger_seq": ...,
          "txn_base_fee": ...,
          "txn_median_fee": ...,
          "recommended_fee_drops": ...,
          "load_factor": ...,
          ... (optionally more fields)
        }
    """

    ts = time.time()
    return {
        "attestation_version": "1.0.0",
        "timestamp": ts,
        "network_state": dict(network_state),
        "meta": {
            "issued_by": "ecosystem.telemetry.make_guardian_attestation",
            "notes": "Read-only VQM telemetry snapshot for policy engines.",
        },
    }
