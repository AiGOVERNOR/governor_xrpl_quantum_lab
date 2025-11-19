"""
VQM Telemetry Layer
High-resolution XRPL telemetry helpers for the Guardian + VQM pipelines.
"""

import time
from typing import Dict, Any


# -------------------------------------------------
# Ledger Close Rate Estimator (LPS)
# -------------------------------------------------
def compute_ledger_rate(ledger_history: list[int]) -> float:
    """
    Estimate ledgers-per-second from recent ledger sequence numbers.
    Safe fallback for short or unstable data.
    """
    if len(ledger_history) < 2:
        return 0.5  # XRPL averages around 3–5 seconds per ledger

    diffs = []
    for i in range(1, len(ledger_history)):
        diffs.append(ledger_history[i] - ledger_history[i - 1])

    avg = sum(diffs) / len(diffs)
    if avg <= 0:
        return 0.5

    # Convert "ledgers per increment" to LPS
    # XRPL typical ledger time ~ 3–5 seconds
    return 1.0 / avg


# -------------------------------------------------
# Fee Band Classifier
# -------------------------------------------------
def classify_fee_band(fee_drops: int) -> str:
    """
    Basic fee band classifier.
    Used for Guardian and network safety signals.
    """
    if fee_drops < 20:
        return "low"
    if fee_drops < 200:
        return "normal"
    if fee_drops < 2000:
        return "elevated"
    return "extreme"


# -------------------------------------------------
# Guardian Attestation Generator
# -------------------------------------------------
def make_guardian_attestation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a Guardian-style human readable attestation
    for VQM Network Policy Layer.
    """
    ledger = state.get("ledger_seq")
    fee = state.get("recommended_fee_drops")
    lf = state.get("load_factor")

    if fee >= 2000:
        mode = "fee_pressure"
        msg = "Fee pressure elevated; recommend adaptive scaling."
    elif lf > 2.0:
        mode = "load_congestion"
        msg = "Network congestion; scale down non-critical operations."
    else:
        mode = "normal"
        msg = "Network metrics nominal."

    return {
        "mode": mode,
        "human_message": msg,
        "ledger": ledger,
        "fee_drops": fee,
        "load_factor": lf,
        "timestamp": time.time(),
    }
