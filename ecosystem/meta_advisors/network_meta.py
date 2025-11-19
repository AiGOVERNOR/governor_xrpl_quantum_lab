from __future__ import annotations

from typing import Any, Dict


def advise_network_posture(neuro: Dict[str, Any], base_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Meta-advisor for overall network posture (from the observer's POV).

    Think of this as high-level operational stance for:
      - node operators
      - indexers / analytics
      - experimental systems
    """
    scores = neuro.get("scores", {})
    signals = neuro.get("signals", {})
    mode = neuro.get("mode", "steady_state")

    load_factor = float(signals.get("load_factor", 1.0) or 1.0)
    coherence = float(scores.get("coherence", 0.8))

    stance = "neutral"
    notes = []

    if mode == "ultra_calm":
        stance = "relaxed"
        notes.append("Plenty of capacity; safe window for maintenance / experiments.")
    elif mode == "steady_state":
        stance = "neutral"
        notes.append("Healthy steady-state. Normal operations recommended.")
    elif mode == "fee_pressure":
        stance = "guarded"
        notes.append("Fee pressure detected. Monitor node health and RPC latency closely.")
    else:
        stance = "alert"
        notes.append("Anomaly risk. Tighten observability and rate-limiting.")

    if coherence < 0.7:
        notes.append("NeuroMesh coherence < 0.7; cross-check fee band vs Guardian policy.")
    if load_factor > 2.0:
        notes.append("High load_factor detected; consider scaling read replicas or RPC capacity.")

    return {
        "advisor": "network_meta_advisor",
        "mode": mode,
        "stance": stance,
        "inputs": {
            "load_factor": load_factor,
            "coherence": coherence,
        },
        "advice": notes,
        "version": "0.1.0",
    }
