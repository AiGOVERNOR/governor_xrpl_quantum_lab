"""
VQM Pipeline v4 – Level 12–30 Super-Brain

This module wraps the base VQM orchestrator with:

- Memory Engine (L12–L15): persists network snapshots on disk
- Predictive Engine (L16–L20): computes fee horizon + trends
- Council Engine (L21–L30): multi-agent governance, scheduler, mesh intent

All behavior is strictly read-only and advisory: no trading, no signing,
no on-ledger side effects.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ecosystem.orchestrator import run_vqm_cycle as base_run_vqm_cycle
from ecosystem.memory import append_state, load_recent_states
from ecosystem.predictive import build_fee_horizon
from ecosystem.council import build_council_decision

PIPELINE_VERSION = "2.0.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_network_state(base: Dict[str, Any]) -> Dict[str, Any]:
    ns = base.get("network_state")
    if isinstance(ns, dict):
        return ns
    return {}


def _build_tools_listing(existing_tools: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    tools = list(existing_tools or [])

    # Ensure base tools are present only once (idempotent).
    def _ensure(name: str, category: str, description: str, version: str = "0.1.0") -> None:
        for t in tools:
            if t.get("name") == name:
                return
        tools.append(
            {
                "name": name,
                "category": category,
                "metadata": {"description": description},
                "score": 0.999,
                "version": version,
            }
        )

    _ensure(
        name="fee_vqm_tool",
        category="fee",
        description="Dynamic XRPL fee band advisor.",
    )
    _ensure(
        name="stream_pay_tool",
        category="payment_protocol",
        description="XRPL StreamPay (salary/stream) protocol logic.",
    )
    _ensure(
        name="escrow_milestone_tool",
        category="escrow",
        description="Milestone escrow protocol planner.",
    )
    _ensure(
        name="fee_pressure_reducer",
        category="network_policy",
        description="AI-guided fee pressure reduction advisor.",
    )
    _ensure(
        name="memory_engine",
        category="infra",
        description="Persistent memory for XRPL network_state snapshots.",
        version="0.2.0",
    )
    _ensure(
        name="predictive_engine",
        category="analytics",
        description="Trend + horizon modeling for XRPL fee conditions.",
        version="0.2.0",
    )
    _ensure(
        name="council_engine",
        category="governance",
        description="Multi-agent council for mesh intent + scheduler.",
        version="0.2.0",
    )

    return tools


def run_vqm_cycle_v4() -> Dict[str, Any]:
    """
    High-level orchestration entry point.

    1. Runs base VQM orchestrator (Guardian + RPC + Mesh).
    2. Appends network_state into disk-backed memory.
    3. Builds fee_horizon using recent history.
    4. Builds council decision: mesh_intent + scheduler + council record.
    5. Returns a rich, fully-composed state object.
    """
    base_state: Dict[str, Any] = base_run_vqm_cycle()
    network_state = _extract_network_state(base_state)

    # 1) Persist to memory (Level 12–15)
    memory_record = {
        "timestamp": _now_iso(),
        "network_state": network_state,
    }
    append_state(memory_record)

    # 2) Load history and build fee horizon (Level 16–20)
    history = load_recent_states(limit=200)
    fee_horizon = build_fee_horizon(history, current_network_state=network_state)

    # 3) Council / Super-brain (Level 21–30)
    council_bundle = build_council_decision(
        network_state=network_state,
        fee_horizon=fee_horizon,
    )

    # 4) Compose tool listing
    existing_tools = base_state.get("tools")
    tools = _build_tools_listing(existing_tools if isinstance(existing_tools, list) else None)

    # 5) Assemble final V4 state
    out: Dict[str, Any] = {}
    out.update(base_state)

    out["pipeline_version"] = PIPELINE_VERSION
    out["timestamp"] = _now_iso()
    out["fee_horizon"] = fee_horizon
    out["mesh_intent"] = council_bundle["mesh_intent"]
    out["scheduler"] = council_bundle["scheduler"]
    out["council"] = council_bundle["council"]
    out["memory"] = {
        "store": "file:data/vqm_memory.jsonl",
        "history_len": len(history),
    }
    out["tools"] = tools

    return out
