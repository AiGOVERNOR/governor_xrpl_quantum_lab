from __future__ import annotations

from typing import Any, Dict, List


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _score_fee_risk(median_fee: int, recommended_fee: int) -> float:
    if median_fee <= 0 or recommended_fee <= 0:
        return 0.1
    ratio = median_fee / float(recommended_fee)
    # 1.0 ≈ normal, >1.0 is worse
    if ratio <= 0.75:
        return 0.2
    if ratio <= 1.25:
        return 0.5
    if ratio <= 2.0:
        return 0.75
    return 0.95


def _score_load_risk(load_factor: float) -> float:
    if load_factor <= 0.5:
        return 0.2
    if load_factor <= 1.0:
        return 0.5
    if load_factor <= 2.0:
        return 0.8
    return 0.98


def _score_guardian_alignment(guardian: Dict[str, Any]) -> float:
    """
    Rough heuristic:
    - attention_required / fee_pressure => higher risk
    - compliant / steady => lower risk
    """
    policy = guardian.get("policy", {})
    status = policy.get("status") or ""
    mode = policy.get("mode") or ""

    score = 0.5
    status = status.lower()
    mode = mode.lower()

    if "attention" in status:
        score += 0.25
    if "non_compliant" in status or "violation" in status:
        score += 0.35
    if "fee_pressure" in mode:
        score += 0.15

    return min(score, 1.0)


def _overall_mode(fee_risk: float, load_risk: float, guardian_risk: float) -> str:
    avg = (fee_risk + load_risk + guardian_risk) / 3.0
    if avg < 0.3:
        return "ultra_calm"
    if avg < 0.6:
        return "steady_state"
    if avg < 0.8:
        return "fee_pressure"
    return "anomaly_risk"


def build_neuromesh_state(base_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the NeuroMesh state from the existing VQM pipeline output.

    Inputs:
      - base_state: full dict returned by ecosystem.pipeline_v4 / v8

    Output:
      - "neuro_mesh" style dict with:
          - scores: fee_risk, load_risk, guardian_alignment
          - overall_mode
          - key signals echoed
    """
    net = base_state.get("network_state", {}) or {}
    guardian = base_state.get("guardian", {}) or {}
    fee_horizon = base_state.get("fee_horizon", {}) or {}
    scheduler = base_state.get("scheduler", {}) or {}
    tools = base_state.get("tools", []) or []

    median_fee = int(net.get("txn_median_fee", 0) or 0)
    recommended_fee = int(net.get("recommended_fee_drops", median_fee or 10) or 10)
    load_factor = float(net.get("load_factor", 1.0) or 1.0)

    fee_risk = _score_fee_risk(median_fee, recommended_fee)
    load_risk = _score_load_risk(load_factor)
    guardian_risk = _score_guardian_alignment(guardian)

    mode = _overall_mode(fee_risk, load_risk, guardian_risk)

    # Pull band/trend if present
    band = fee_horizon.get("projected_fee_band") or _safe_get(
        base_state, ["mesh_intent", "inputs", "band"], "unknown"
    )
    trend_short = _safe_get(base_state, ["fee_horizon", "trend_short", "direction"], "flat")
    trend_long = _safe_get(base_state, ["fee_horizon", "trend_long", "direction"], "flat")

    # Very simple "coherence" metric: do mode & band roughly agree?
    coherence = 1.0
    if mode == "fee_pressure" and band == "normal":
        coherence = 0.7
    elif mode in ("ultra_calm", "steady_state") and band in ("elevated", "extreme"):
        coherence = 0.6

    # Tools with best scores (0..1)
    top_tools = sorted(
        [
            {"name": t.get("name"), "category": t.get("category"), "score": t.get("score", 0.0)}
            for t in tools
        ],
        key=lambda x: x["score"],
        reverse=True,
    )[:5]

    return {
        "mode": mode,
        "scores": {
            "fee_risk": fee_risk,
            "load_risk": load_risk,
            "guardian_alignment": guardian_risk,
            "coherence": coherence,
        },
        "signals": {
            "ledger_seq": net.get("ledger_seq"),
            "median_fee": median_fee,
            "recommended_fee": recommended_fee,
            "load_factor": load_factor,
            "fee_band": band,
            "trend_short": trend_short,
            "trend_long": trend_long,
        },
        "scheduler_snapshot": {
            "band": scheduler.get("band"),
            "job_count": len(scheduler.get("jobs", [])),
        },
        "top_tools": top_tools,
        "version": "0.1.0",
    }
