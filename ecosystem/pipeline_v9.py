from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

# We layer V9+ on top of the already-working V4 pipeline.
from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as base_run_vqm_cycle


def _get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    return d.get(key, default) if isinstance(d, dict) else default


# ---------------------------------------------------------------------------
# V9: Predictive Flow Engine (no trading, read-only, advisory only)
# ---------------------------------------------------------------------------

def _predictive_flow_layer(base_state: Dict[str, Any]) -> Dict[str, Any]:
    network = _get(base_state, "network_state", {})
    fee_h = _get(base_state, "fee_horizon", {})

    median = _get(network, "txn_median_fee", 10) or 10
    load_factor = float(_get(network, "load_factor", 1.0) or 1.0)

    band = (
        _get(fee_h, "projected_fee_band")
        or _get(fee_h, "band")
        or "unknown"
    )

    short_trend = _get(fee_h, "trend_short", {})
    long_trend = _get(fee_h, "trend_long", {})

    # Very lightweight risk scoring – purely analytical.
    risk = 0.10  # base
    if band == "extreme":
        risk += 0.70
    elif band == "elevated":
        risk += 0.40
    elif band == "normal":
        risk += 0.10

    if median >= 10000:
        risk += 0.30
    elif median >= 5000:
        risk += 0.15
    elif median <= 20:
        risk -= 0.05

    # Load factor nudge.
    if load_factor >= 3.0:
        risk += 0.30
    elif load_factor >= 2.0:
        risk += 0.15
    elif load_factor <= 1.0:
        risk -= 0.05

    # Clamp to [0, 1]
    risk = max(0.0, min(1.0, risk))

    if risk < 0.25:
        scenario = "calm"
    elif risk < 0.55:
        scenario = "build_up"
    elif risk < 0.8:
        scenario = "pressure"
    else:
        scenario = "storm_risk"

    return {
        "version": "0.1.0",
        "scenario": scenario,
        "risk_score": risk,
        "median_fee_drops": median,
        "load_factor": load_factor,
        "band": band,
        "short_trend": short_trend,
        "long_trend": long_trend,
        "notes": (
            "Purely advisory, no-transactions predictive read of fee "
            "pressure and load. Designed for mainnet-safe dashboards."
        ),
    }


# ---------------------------------------------------------------------------
# V10: Node Trust Mesh (advisory only, no RPC writes)
# ---------------------------------------------------------------------------

def _node_trust_mesh_layer(
    base_state: Dict[str, Any],
    predictive: Dict[str, Any],
) -> Dict[str, Any]:
    band = predictive.get("band", "unknown")
    risk = float(predictive.get("risk_score", 0.0))

    # Static list of known endpoints – you can expand this later.
    nodes: List[Dict[str, Any]] = [
        {
            "name": "xrpl_main_s1",
            "url": "https://s1.ripple.com:51234",
            "role": "primary",
            "base_trust": 0.95,
        },
        {
            "name": "xrpl_main_s2",
            "url": "https://s2.ripple.com:51234",
            "role": "secondary",
            "base_trust": 0.92,
        },
        {
            "name": "xrpl_cluster_a",
            "url": "https://xrplcluster.com",
            "role": "edge",
            "base_trust": 0.88,
        },
    ]

    # Adjust trust slightly based on global band/risk, but never below 0.5.
    adjusted_nodes: List[Dict[str, Any]] = []
    for n in nodes:
        base_trust = float(n["base_trust"])
        delta = 0.0

        if band == "extreme" or risk >= 0.8:
            delta = -0.10
        elif band == "elevated" or risk >= 0.55:
            delta = -0.05
        elif band == "calm" and risk <= 0.25:
            delta = +0.02

        adj = max(0.5, min(1.0, base_trust + delta))
        m = dict(n)
        m["adjusted_trust"] = round(adj, 3)
        adjusted_nodes.append(m)

    # Global summary – just a coarse health string.
    if risk >= 0.8:
        global_health = "stress"
    elif risk >= 0.55:
        global_health = "watch"
    else:
        global_health = "healthy"

    return {
        "version": "0.1.0",
        "global_health": global_health,
        "nodes": adjusted_nodes,
        "inputs": {
            "band": band,
            "risk_score": risk,
        },
        "notes": (
            "Advisory trust/view layer only. Does not send transactions, "
            "does not reconfigure nodes – safe to run against mainnet."
        ),
    }


# ---------------------------------------------------------------------------
# V11: Governance / Safety Envelope (read-only recommendations)
# ---------------------------------------------------------------------------

def _governance_layer(
    base_state: Dict[str, Any],
    predictive: Dict[str, Any],
    node_trust: Dict[str, Any],
) -> Dict[str, Any]:
    guardian = _get(base_state, "guardian", {})
    guardian_policy = _get(guardian, "policy", {})
    guardian_mode = (
        _get(guardian_policy, "mode")
        or _get(_get(guardian, "mesh", {}), "mode")
        or "unknown"
    )

    band = predictive.get("band", "unknown")
    risk = float(predictive.get("risk_score", 0.0))
    node_health = node_trust.get("global_health", "unknown")

    if risk < 0.25:
        risk_tier = "low"
    elif risk < 0.55:
        risk_tier = "moderate"
    elif risk < 0.8:
        risk_tier = "elevated"
    else:
        risk_tier = "critical"

    controls: List[str] = []

    # Always non-trading, observability-only recommendations.
    if risk_tier in ("low", "moderate"):
        controls.append("Normal observability; keep VQM telemetry running.")
    if risk_tier in ("elevated", "critical"):
        controls.append("Intensify telemetry & logging around fee changes.")
        controls.append("Flag fee bands in dashboards as 'attention required'.")
    if band in ("extreme", "elevated"):
        controls.append("Highlight non-essential / complex flows in monitoring.")

    if node_health == "stress":
        controls.append("Review node diversity; prefer high-trust RPC endpoints.")

    flags = {
        "safe_to_continue": risk_tier in ("low", "moderate"),
        "halt_recommended": False,  # Analytics-only, never halts flows itself.
        "extra_observability": risk_tier in ("elevated", "critical"),
    }

    return {
        "version": "0.1.0",
        "status": "attention_required" if risk_tier in ("elevated", "critical") else "normal",
        "risk_tier": risk_tier,
        "controls": controls,
        "flags": flags,
        "meta": {
            "guardian_mode": guardian_mode,
            "band": band,
            "node_global_health": node_health,
            "risk_score": risk,
        },
        "notes": (
            "Governance envelope for XRPL VQM: recommendations only. "
            "No transaction creation, no key use, no automated trading."
        ),
    }


# ---------------------------------------------------------------------------
# Public entrypoint: V9+ master cycle
# ---------------------------------------------------------------------------

def run_vqm_cycle_v9() -> Dict[str, Any]:
    """
    Level-9+ VQM cycle.

    1) Runs the existing V4 pipeline (network_state, guardian, fee_horizon, etc.).
    2) Derives predictive fee / load scenarios.
    3) Builds a node trust mesh (advisory only).
    4) Builds a governance/safety envelope.
    """
    base = base_run_vqm_cycle()

    predictive = _predictive_flow_layer(base)
    node_trust = _node_trust_mesh_layer(base, predictive)
    governance = _governance_layer(base, predictive, node_trust)

    enriched: Dict[str, Any] = dict(base)
    enriched["pipeline_version"] = "1.9.0"
    enriched["timestamp"] = datetime.now(timezone.utc).isoformat()
    enriched["predictive_flow"] = predictive
    enriched["node_trust_mesh"] = node_trust
    enriched["governance_v1"] = governance

    return enriched
