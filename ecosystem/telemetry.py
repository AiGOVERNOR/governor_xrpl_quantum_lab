"""
Telemetry + classification helpers for the VQM XRPL ecosystem.
No network I/O here, just pure math / shaping logic.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LedgerRate:
    ledger_seq: int
    ledgers_per_second: Optional[float]
    seconds_per_ledger: Optional[float]


@dataclass
class FeeBand:
    recommended_drops: int
    band: str
    comment: str


def compute_ledger_rate(
    current_seq: int,
    current_ts: float,
    prev_seq: Optional[int],
    prev_ts: Optional[float],
) -> LedgerRate:
    """
    Computes approximate ledger close rate between two observations.
    If we don't have previous state, returns None-derived rate fields.
    """
    if prev_seq is None or prev_ts is None:
        return LedgerRate(
            ledger_seq=current_seq,
            ledgers_per_second=None,
            seconds_per_ledger=None,
        )

    delta_ledgers = current_seq - prev_seq
    delta_time = current_ts - prev_ts

    if delta_ledgers <= 0 or delta_time <= 0:
        return LedgerRate(
            ledger_seq=current_seq,
            ledgers_per_second=None,
            seconds_per_ledger=None,
        )

    lps = float(delta_ledgers) / float(delta_time)
    spl = 1.0 / lps if lps > 0 else None

    return LedgerRate(
        ledger_seq=current_seq,
        ledgers_per_second=lps,
        seconds_per_ledger=spl,
    )


def classify_fee_band(
    base_drops: int,
    median_drops: int,
    recommended_drops: int,
) -> FeeBand:
    """
    Puts current fees into qualitative buckets so VQM/Guardian
    can reason in human language and rules.
    """
    # Normalize by base fee for rough scale.
    multiplier = recommended_drops / max(base_drops, 1)

    if multiplier <= 2:
        band = "low"
        comment = "Plenty of headroom; fees are cheap."
    elif multiplier <= 10:
        band = "normal"
        comment = "Healthy fee regime for retail flows."
    elif multiplier <= 50:
        band = "elevated"
        comment = "Network under noticeable pressure."
    else:
        band = "extreme"
        comment = "Backpressure / congestion; throttle non-critical flows."

    return FeeBand(
        recommended_drops=recommended_drops,
        band=band,
        comment=comment,
    )


def make_guardian_attestation(
    snapshot: Dict[str, Any],
    federation_id: Optional[str] = None,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an unsigned attestation document suitable for logging or
    later signing by an offline key. This is intentionally generic.
    """
    ts = time.time()
    payload = {
        "timestamp": ts,
        "snapshot": snapshot,
        "federation_id": federation_id,
        "node_id": node_id,
    }

    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    checksum = hashlib.sha256(raw).hexdigest()

    return {
        "attestation_id": checksum,
        "timestamp": ts,
        "federation_id": federation_id,
        "node_id": node_id,
        "checksum": checksum,
        "payload": payload,
    }
