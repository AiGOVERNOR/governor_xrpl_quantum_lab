"""
Telemetry — Fee Band Classification
"""

def classify_fee_band(median_fee_drops: int, load_factor: float) -> dict:
    """
    Classifies network fee pressure into: LOW / NORMAL / ELEVATED / EXTREME.

    XRP Ledger reference:
    - Very low median fees: < 20 drops
    - Normal fees: 20–100 drops
    - Elevated fees: 100–2000 drops
    - Extreme: > 2000 or load_factor > 4
    """

    if load_factor > 4:
        return {"band": "extreme", "comment": "Severe network load"}

    if median_fee_drops > 2000:
        return {"band": "extreme", "comment": "High fee spike"}

    if median_fee_drops > 100:
        return {"band": "elevated", "comment": "Busy ledger"}

    if median_fee_drops > 20:
        return {"band": "normal", "comment": "Typical XRPL network"}

    return {"band": "low", "comment": "Quiet network"}
