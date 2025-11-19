"""
Guardian Layer – VQM Level-3 Adaptive Policy Engine
---------------------------------------------------
Reads normalized network_state from orchestrator
and generates:

- mesh state
- forge suggestions
- LLM-style guidance
- network policy proposal
- fee pressure mode handling
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Any, Dict


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def guardian_cycle(network_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point used by orchestrator and pipeline_v4.

    Input:
        network_state = {
            "ledger_seq": ...,
            "txn_base_fee": ...,
            "txn_median_fee": ...,
            "recommended_fee_drops": ...,
            "load_factor": ...
        }

    Output:
        Fully structured Guardian state.
    """

    median = network_state.get("txn_median_fee", 0)
    load_factor = network_state.get("load_factor", 1.0)
    ledger = network_state.get("ledger_seq", 0)

    # -------------------------
    # Determine mode
    # -------------------------
    if median >= 8000 or load_factor >= 3:
        mode = "extreme_pressure"
    elif median >= 3000 or load_factor >= 1.5:
        mode = "fee_pressure"
    else:
        mode = "normal"

    # -------------------------
    # Forge suggestions
    # -------------------------
    if mode == "normal":
        forge_suggestions = [
            "Maintain current fee band.",
            "Monitor ledger rate; no intervention needed.",
            "Continue sampling XRPL nodes."
        ]
    elif mode == "fee_pressure":
        forge_suggestions = [
            "Tighten fee band for non-essential flows.",
            "Prioritize simple, low-cost transactions.",
            "Promote StreamPay + Escrow protocols over complex paths.",
        ]
    else:  # extreme_pressure
        forge_suggestions = [
            "Enforce maximum priority on essential payments.",
            "Deny complex high-cost tx classes.",
            "Raise recommended_fee_drops short-term.",
        ]

    # -------------------------
    # LLM guidance
    # -------------------------
    llm_guidance = {
        "explanation": f"Guardian detected mode={mode}. Median fee {median} drops. Load factor={load_factor}.",
        "human_context": f"Ledger {ledger}, median_fee={median}, load_factor={load_factor}",
        "mode": mode,
        "policy_id": str(uuid.uuid4()),
    }

    # -------------------------
    # Mesh
    # -------------------------
    mesh = {
        "ledger": ledger,
        "mode": mode,
        "fee_drops": median,
        "load_factor": load_factor,
    }

    # -------------------------
    # Policy Proposal
    # -------------------------
    policy = {
        "id": llm_guidance["policy_id"],
        "category": "network_policy",
        "status": "compliant" if mode == "normal" else "attention_required",
        "created_at": _iso_now(),
        "mode": mode,
        "payload": {
            "ledger": ledger,
            "txn_median_fee": median,
            "load_factor": load_factor,
            "recommended_fee": network_state.get("recommended_fee_drops", median),
        },
    }

    # -------------------------
    # Final Guardian State
    # -------------------------
    return {
        "mesh": mesh,
        "llm": llm_guidance,
        "policy": policy,
        "forge": {
            "inferred_mode": mode,
            "status": "draft",
            "suggested_changes": forge_suggestions,
            "upgrade_id": str(uuid.uuid4()),
        },
    }
