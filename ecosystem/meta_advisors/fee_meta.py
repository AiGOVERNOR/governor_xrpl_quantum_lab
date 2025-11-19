from __future__ import annotations

from typing import Any, Dict


def advise_fee_strategy(neuro: Dict[str, Any], base_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given NeuroMesh state + base pipeline state, produce a synthetic
    "fee meta-advisor" output.

    This is where you plug in smarter logic over time.
    """
    scores = neuro.get("scores", {})
    signals = neuro.get("signals", {})
    mode = neuro.get("mode", "steady_state")

    fee_risk = float(scores.get("fee_risk", 0.5))
    band = signals.get("fee_band", "unknown")
    median_fee = int(signals.get("median_fee", 0) or 0)
    recommended_fee = int(signals.get("recommended_fee", 0) or 0)

    notes = []
    profile = "balanced"

    if mode == "ultra_calm":
        notes.append("Network appears ultra-calm; fees are not constraining flows.")
        profile = "expansive"
    elif mode == "steady_state":
        notes.append("Network appears steady; normal fee policies are appropriate.")
        profile = "balanced"
    elif mode == "fee_pressure":
        notes.append("Fee pressure detected; encourage efficient protocols (StreamPay, minimal hops).")
        profile = "defensive"
    else:
        notes.append("Potential anomaly risk; be conservative with complex flows.")
        profile = "defensive"

    if band in ("elevated", "extreme"):
        notes.append(f"Fee band={band}. Consider nudging wallets to pre-quote fees and show ranges.")
    if median_fee > recommended_fee:
        notes.append("Median fee above recommendation; highlight fee transparency to users/integrators.")

    return {
        "advisor": "fee_meta_advisor",
        "mode": mode,
        "profile": profile,
        "inputs": {
            "fee_risk": fee_risk,
            "band": band,
            "median_fee": median_fee,
            "recommended_fee": recommended_fee,
        },
        "advice": notes,
        "version": "0.1.0",
    }
