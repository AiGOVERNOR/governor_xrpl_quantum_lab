"""
quantum_fusion.py
Governor XRPL Quantum Lab — Quantum Signal Engine v2.0

This module consolidates all quantum-band computation into a single,
contract-compliant engine that integrates with:

 - flow_engine
 - multileg
 - router_v3
 - protocol_graph
 - sdk_client
 - vqm_doctor_cli

RULES:
  • compute_quantum_signal(network_state: Dict[str, Any]) is the ONLY public API.
  • network_state may be incomplete; engine must SELF-HEAL missing fields.
  • Fusion output must ALWAYS conform to quantum_signal_contract_v2 structure.
"""

from typing import Dict, Any


QUANTUM_VERSION = "2.0.0"


# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------

def _safe_get(d: Dict[str, Any], key: str, default: Any) -> Any:
    """Self-healing get() that normalizes incorrect types."""
    v = d.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def _compute_band(median_fee: float, load_factor: float) -> str:
    """
    Canonical band rules across all engines.
    """
    if load_factor >= 1.4 or median_fee >= 8000:
        return "extreme"
    if load_factor >= 1.1 or median_fee >= 6000:
        return "elevated"
    return "normal"


def _compute_pressure_score(median_fee: float, recommended_fee: float) -> float:
    if recommended_fee <= 0:
        return 0.0
    score = median_fee / recommended_fee
    if score < 0:
        return 0.0
    if score > 2:
        return 2.0
    return round(score, 4)


def _determine_guardian_mode(band: str, pressure: float) -> str:
    if band == "extreme" or pressure >= 1.0:
        return "fee_pressure"
    if band == "elevated":
        return "caution"
    return "normal"


# ---------------------------------------------------------
# PUBLIC API — REQUIRED BY CONTRACT
# ---------------------------------------------------------

def compute_quantum_signal(network_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Canonical quantum signal used by all engines.

    Accepted network_state fields:
        ledger_seq, median_fee, recommended_fee, load_factor

    Missing fields are auto-healed.

    Returns dict:
        {
          "version": QUANTUM_VERSION,
          "median_fee_drops": ...,
          "recommended_fee_drops": ...,
          "safe_fee_drops": ...,
          "band": "...",
          "guardian_mode": "...",
          "pressure_score": ...,
          "attention_required": bool,
          "trend": "flat",
          "notes": [...]
        }
    """

    # ---- Self-heal missing or bad fields ------------------
    median_fee = _safe_get(network_state, "txn_median_fee", 5000)
    recommended_fee = _safe_get(network_state, "recommended_fee_drops", median_fee)
    load_factor = _safe_get(network_state, "load_factor", 1.0)

    # ---- Compute attributes -------------------------------
    band = _compute_band(median_fee, load_factor)
    pressure = _compute_pressure_score(median_fee, recommended_fee)
    guardian_mode = _determine_guardian_mode(band, pressure)
    safe_fee = int(max(median_fee * 1.10, recommended_fee))

    attention_required = band in ("elevated", "extreme") or pressure >= 1.0

    notes = [
        f"band={band}, load_factor={load_factor}",
        f"median_fee={median_fee}, recommended_fee={recommended_fee}, safe_fee={safe_fee}",
        f"pressure={pressure}, guardian_mode={guardian_mode}"
    ]

    # ---- Final quantum dict -------------------------------
    return {
        "version": QUANTUM_VERSION,
        "median_fee_drops": int(median_fee),
        "recommended_fee_drops": int(recommended_fee),
        "safe_fee_drops": int(safe_fee),
        "band": band,
        "guardian_mode": guardian_mode,
        "pressure_score": pressure,
        "attention_required": attention_required,
        "trend": "flat",
        "load_factor": load_factor,
        "notes": notes,
    }


# ---------------------------------------------------------
# OPTIONAL PUBLIC RUNNER
# Used by ecosystem.cli.quantum_fusion_cli
# ---------------------------------------------------------

def run_quantum_fusion(network_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper used by CLI tools.
    """
    return compute_quantum_signal(network_state)
