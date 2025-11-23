"""
ecosystem.telemetry
-------------------
Quantum telemetry tools for VQM.
All functions are SAFE, read-only, mainnet-compatible.
"""

from typing import Any, Dict, List


def compute_ledger_rate(history: List[int]) -> Dict[str, float]:
    if not history or len(history) < 2:
        return {"ledgers_per_second": 0.0, "seconds_per_ledger": 0.0}

    deltas = [history[i] - history[i - 1] for i in range(1, len(history))]
    avg = sum(deltas) / len(deltas) if deltas else 0.0

    if avg <= 0:
        return {"ledgers_per_second": 0.0, "seconds_per_ledger": 0.0}

    lps = 1.0 / avg
    return {"ledgers_per_second": lps, "seconds_per_ledger": avg}


def classify_fee_band(
    median_fee: int = None,
    median_fee_drops: int = None,
    load_factor: float = 1.0
) -> Dict[str, Any]:
    """
    Backwards + forwards compatible fee band classifier.
    Accepts:
      - classify_fee_band(median_fee=...)
      - classify_fee_band(median_fee_drops=...)
    """
    # Normalize input
    fee = median_fee_drops if median_fee_drops is not None else median_fee
    if fee is None:
        return {"band": "unknown", "comment": "No fee provided"}

    # Fee band logic
    if fee <= 20:
        return {"band": "low", "comment": "Network inexpensive"}
    elif fee <= 200:
        return {"band": "normal", "comment": "Healthy fee level"}
    elif fee <= 2000:
        return {"band": "elevated", "comment": "Busy period"}
    else:
        return {"band": "extreme", "comment": "High congestion"}



def make_guardian_attestation(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": "1.0.0",
        "ledger": snapshot.get("ledger_seq"),
        "median_fee": snapshot.get("txn_median_fee"),
        "load_factor": snapshot.get("load_factor"),
    }


# ----------------------------
# NEW QUANTUM TELEMETRY TOOLS
# ----------------------------

def anomaly_detect(history: List[int]) -> Dict[str, Any]:
    """
    Detect anomalies in median_fee or ledger rate.
    Purely analytical — NEVER interacts with the network.
    """
    if len(history) < 3:
        return {"anomaly": False, "reason": "insufficient data"}

    diffs = [abs(history[i] - history[i - 1]) for i in range(1, len(history))]
    avg = sum(diffs) / len(diffs)

    # simple spike model
    spike = diffs[-1] > (avg * 3)

    return {
        "anomaly": spike,
        "reason": "fee spike detected" if spike else "normal variance",
    }


def predict_fee_trend(history: List[int]) -> Dict[str, str]:
    """
    Basic trend predictor:
      - rising, falling, or flat
    """
    if len(history) < 3:
        return {"trend": "flat"}

    if not isinstance(history, list):
        return {"trend": "flat", "reason": "non-list input"}
    
    prev = history[-2]
    pre_prev = history[-3]

    if last > prev > pre_prev:
        return {"trend": "rising"}
    if last < prev < pre_prev:
        return {"trend": "falling"}
    return {"trend": "flat"}
