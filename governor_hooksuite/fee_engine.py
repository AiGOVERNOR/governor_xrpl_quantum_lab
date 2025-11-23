from __future__ import annotations

from typing import Optional

from .models import FeePolicy


def compute_fee_drops(amount_drops: int, policy: FeePolicy) -> int:
    """
    Compute fee in drops according to a FeePolicy.

    - fee = amount * bps / 10_000, with:
        * min_drops enforced
        * max_bps enforced as a safety cap
    """
    if amount_drops <= 0:
        return 0

    bps = min(max(policy.bps, 0), policy.max_bps)
    raw = (amount_drops * bps) // 10_000

    fee = max(raw, policy.min_drops)
    return fee

