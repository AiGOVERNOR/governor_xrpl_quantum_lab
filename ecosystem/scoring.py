"""
ecosystem.scoring
-----------------
VQM Score Layer (Level 4-ish):

- Computes a global confidence score for the current XRPL view.
- Derives effective per-tool scores based on:
  * fee band
  * load_factor
  * guardian policy status
  * short-term fee trend (if available)
- Adds explanations so humans + higher-level AI can reason about trust.

This module is PURELY READ-ONLY and side-effect free:
it only consumes the JSON-like 'state' dict and returns an enriched copy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _band_weight(band: str) -> float:
    band = (band or "").lower()
    if band in ("low", "cheap"):
        return 1.02
    if band in ("normal", "steady_state"):
        return 1.0
    if band in ("elevated",):
        return 0.9
    if band in ("extreme", "stress", "fee_pressure"):
        return 0.75
    return 0.95


def _trend_weight(trend_short: str | None) -> float:
    trend_short = (trend_short or "").lower()
    if trend_short in ("down", "falling", "cooling"):
        return 1.02
    if trend_short in ("flat", "steady"):
        return 1.0
    if trend_short in ("up", "rising", "heating"):
        return 0.9
    return 1.0


def _guardian_status_weight(status: str | None) -> float:
    status = (status or "").lower()
    if status == "compliant":
        return 1.03
    if status == "attention_required":
        return 0.93
    if status == "violation":
        return 0.8
    return 1.0


def _load_factor_weight(load_factor: float) -> float:
    if load_factor <= 1.5:
        return 1.03
    if load_factor <= 2.0:
        return 0.98
    if load_factor <= 3.0:
        return 0.9
    return 0.8


def _clamp_score(x: float, lo: float = 0.0, hi: float = 0.999) -> float:
    return max(lo, min(hi, x))


def _extract_band_and_trend(state: Dict[str, Any]) -> Tuple[str, str]:
    band = ""
    trend_short = ""

    fee_horizon = state.get("fee_horizon") or {}
    if isinstance(fee_horizon, dict):
        band = fee_horizon.get("projected_fee_band") or band
        ts = fee_horizon.get("trend_short") or {}
        if isinstance(ts, dict):
            trend_short = ts.get("direction") or trend_short

    mesh_intent = state.get("mesh_intent") or {}
    if isinstance(mesh_intent, dict):
        inputs = mesh_intent.get("inputs") or {}
        if isinstance(inputs, dict):
            band = inputs.get("band") or band
            trend_short = inputs.get("trend_short") or trend_short

    scheduler = state.get("scheduler") or {}
    if isinstance(scheduler, dict):
        band = scheduler.get("band") or band

    return band, trend_short


def _extract_guardian_status(state: Dict[str, Any]) -> Tuple[str, str]:
    guardian = state.get("guardian") or {}
    if not isinstance(guardian, dict):
        return "", ""

    policy = guardian.get("policy") or {}
    if not isinstance(policy, dict):
        return "", ""

    status = policy.get("status") or ""
    mode = policy.get("mode") or ""
    return status, mode


def _extract_load_factor_and_median(state: Dict[str, Any]) -> Tuple[float, float]:
    ns = state.get("network_state") or {}
    if not isinstance(ns, dict):
        return 1.0, 0.0
    lf = float(ns.get("load_factor", 1.0) or 1.0)
    median = float(ns.get("txn_median_fee", 0.0) or 0.0)
    return lf, median


def compute_global_confidence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a global confidence score for the entire snapshot.

    This does NOT decide "good/bad", it decides
    "how much can we trust this view + these tools right now?"
    """
    band, trend_short = _extract_band_and_trend(state)
    guardian_status, guardian_mode = _extract_guardian_status(state)
    load_factor, median_fee = _extract_load_factor_and_median(state)

    reasons: List[str] = []

    base = 0.92
    reasons.append("Base global confidence: 0.92")

    bw = _band_weight(band)
    base *= bw
    reasons.append(f"Band '{band or 'unknown'}' → weight {bw:.3f}")

    tw = _trend_weight(trend_short)
    base *= tw
    if trend_short:
        reasons.append(f"Short-term trend '{trend_short}' → weight {tw:.3f}")
    else:
        reasons.append("No short-term trend info → neutral weight 1.000")

    gw = _guardian_status_weight(guardian_status)
    base *= gw
    if guardian_status:
        reasons.append(f"Guardian status '{guardian_status}' → weight {gw:.3f}")
    else:
        reasons.append("No guardian status → neutral weight 1.000")

    lw = _load_factor_weight(load_factor)
    base *= lw
    reasons.append(f"Load factor {load_factor:.2f} → weight {lw:.3f}")

    if median_fee > 0 and median_fee > 5000:
        base *= 0.95
        reasons.append(
            f"Median fee {median_fee:.0f} drops is high vs typical retail → weight 0.950"
        )

    score = _clamp_score(base)
    reasons.append(f"Clamped global confidence → {score:.3f}")

    return {
        "global_confidence": round(score, 3),
        "band": band or "unknown",
        "trend_short": trend_short or "unknown",
        "guardian_status": guardian_status or "unknown",
        "guardian_mode": guardian_mode or "unknown",
        "load_factor": load_factor,
        "median_fee": median_fee,
        "reasons": reasons,
    }


def enrich_with_scores(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a VQM pipeline state dict with:
      - scores.global_confidence (0–0.999)
      - per-tool effective scores and reasons
    """
    if not isinstance(state, dict):
        return state

    meta = compute_global_confidence(state)
    global_conf = meta["global_confidence"]

    tools = state.get("tools") or []
    enriched_tools = []

    for tool in tools:
        if not isinstance(tool, dict):
            enriched_tools.append(tool)
            continue

        base_score = float(tool.get("score", 1.0) or 1.0)
        tool_name = tool.get("name", "unknown")
        category = (tool.get("category") or "unknown").lower()

        category_weight = 1.0
        cat_reason = "neutral"
        if category in ("fee", "network_policy"):
            category_weight = 1.02
            cat_reason = "slight bias ↑ for fee/network_policy tools"
        elif category in ("payment_protocol", "escrow"):
            category_weight = 0.99
            cat_reason = "slight bias ↓ for higher-level protocols under uncertainty"

        effective = _clamp_score(global_conf * base_score * category_weight)

        reasons = [
            f"Base tool score={base_score:.3f}",
            f"Global confidence={global_conf:.3f}",
            f"Category='{category}' → weight {category_weight:.3f} ({cat_reason})",
        ]

        tool_meta = {
            "effective_score": round(effective, 3),
            "global_confidence": global_conf,
            "category_weight": category_weight,
            "explanations": reasons,
        }

        new_tool = dict(tool)
        new_tool["score_meta"] = tool_meta
        enriched_tools.append(new_tool)

    new_state = dict(state)
    new_state["tools"] = enriched_tools
    new_state["scores"] = meta
    return new_state
