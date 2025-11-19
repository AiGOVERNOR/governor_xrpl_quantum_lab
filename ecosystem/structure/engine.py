from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
import uuid


Status = Literal["stable", "degraded", "critical"]


@dataclass
class ComponentSnapshot:
    name: str
    category: str
    status: Status
    score: float
    notes: str


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _build_structural_map(base_state: Dict[str, Any]) -> List[ComponentSnapshot]:
    components: List[ComponentSnapshot] = []

    net = base_state.get("network_state", {})
    guardian = base_state.get("guardian", {})
    fee_horizon = base_state.get("fee_horizon", {})
    scheduler = base_state.get("scheduler", {})
    tools = base_state.get("tools", [])

    load_factor = float(net.get("load_factor", 1.0) or 1.0)
    median_fee = int(net.get("txn_median_fee", 10) or 10)

    # RPC / Telemetry "virtual" components
    rpc_score = 0.95
    if load_factor > 3.0:
        rpc_score -= 0.1

    components.append(
        ComponentSnapshot(
            name="xrpl_rpc_layer",
            category="rpc",
            status="stable",
            score=rpc_score,
            notes="Multi-node XRPL observer (read-only).",
        )
    )

    components.append(
        ComponentSnapshot(
            name="telemetry_core",
            category="telemetry",
            status="stable",
            score=0.95,
            notes="Fee horizon, band classification, and mesh telemetry.",
        )
    )

    # Guardian
    policy_status = _safe_get(guardian, ["policy", "status"], "unknown")
    guardian_score: float = 0.9
    guardian_status: Status = "stable"

    if policy_status == "attention_required":
        guardian_score = 0.8
        guardian_status = "degraded"
    elif policy_status == "non_compliant":
        guardian_score = 0.6
        guardian_status = "critical"

    components.append(
        ComponentSnapshot(
            name="guardian_ai",
            category="network_policy",
            status=guardian_status,
            score=guardian_score,
            notes=f"Guardian policy status={policy_status}.",
        )
    )

    # Fee horizon
    if fee_horizon:
        components.append(
            ComponentSnapshot(
                name="fee_horizon",
                category="forecast",
                status="stable",
                score=0.9,
                notes="Short vs long trend estimator for fee dynamics.",
            )
        )

    # Scheduler
    if scheduler:
        components.append(
            ComponentSnapshot(
                name="infra_scheduler",
                category="infra",
                status="stable",
                score=0.9,
                notes="Job concurrency planner over bands / modes.",
            )
        )

    # Tools -> each is a component
    for t in tools:
        t_name = t.get("name", "unnamed_tool")
        t_cat = t.get("category", "generic")
        raw_score = float(t.get("score", 0.8) or 0.8)

        if raw_score >= 0.9:
            status: Status = "stable"
        elif raw_score >= 0.7:
            status = "degraded"
        else:
            status = "critical"

        components.append(
            ComponentSnapshot(
                name=t_name,
                category=f"tool::{t_cat}",
                status=status,
                score=raw_score,
                notes=t.get("metadata", {}).get("description", "").strip()
                or "VQM tool.",
            )
        )

    # Mesh intent + horizon as higher-level
    if base_state.get("mesh_intent"):
        components.append(
            ComponentSnapshot(
                name="mesh_intent_engine",
                category="coordination",
                status="stable",
                score=0.92,
                notes="Turns band + horizon into human / infra advice.",
            )
        )

    # Basic network pressure hint
    if median_fee >= 5000:
        components.append(
            ComponentSnapshot(
                name="fee_pressure_context",
                category="context",
                status="degraded",
                score=0.78,
                notes="Median fees elevated; network in or near fee pressure band.",
            )
        )

    return components


def _evaluate_health(components: List[ComponentSnapshot]) -> Dict[str, Any]:
    if not components:
        return {
            "infra_state": "UNKNOWN",
            "avg_component_score": 0.0,
            "counts": {"stable": 0, "degraded": 0, "critical": 0},
        }

    total_score = 0.0
    counts = {"stable": 0, "degraded": 0, "critical": 0}
    for c in components:
        total_score += c.score
        counts[c.status] += 1

    avg_score = total_score / len(components)

    if counts["critical"] > 0:
        infra_state = "RED"
    elif counts["degraded"] > 0 or avg_score < 0.85:
        infra_state = "YELLOW"
    else:
        infra_state = "GREEN"

    return {
        "infra_state": infra_state,
        "avg_component_score": round(avg_score, 3),
        "counts": counts,
    }


def _plan_upgrades(
    components: List[ComponentSnapshot],
    health: Dict[str, Any],
    base_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    for c in components:
        if c.status == "stable":
            continue

        severity = "high" if c.status == "critical" else "medium"

        suggestions.append(
            {
                "id": str(uuid.uuid4()),
                "component": c.name,
                "category": c.category,
                "severity": severity,
                "status": c.status,
                "rationale": f"Component score={c.score:.3f}, status={c.status}.",
                "recommended_actions": [
                    "Review assumptions and thresholds.",
                    "Add more explicit logging / telemetry around this component.",
                    "Simulate edge scenarios against captured XRPL snapshots.",
                ],
            }
        )

    # Global upgrade hints based on infra_state
    infra_state = health.get("infra_state")
    if infra_state in ("YELLOW", "RED"):
        suggestions.append(
            {
                "id": str(uuid.uuid4()),
                "component": "vqm_infra",
                "category": "meta",
                "severity": "medium" if infra_state == "YELLOW" else "high",
                "status": infra_state.lower(),
                "rationale": f"Infra_state={infra_state} with average score={health.get('avg_component_score')}.",
                "recommended_actions": [
                    "Capture longer-term fee horizon snapshots.",
                    "Add replay harness for XRPL fee and ledger telemetry.",
                    "Expose structure_state via API endpoint for external dashboards.",
                ],
            }
        )

    return suggestions


def _generate_evolution_drafts(
    components: List[ComponentSnapshot],
    health: Dict[str, Any],
    base_state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    These are blueprints, not live code.
    They describe future internal tools/pipelines that a human
    (you) can choose to implement, extend, or ignore.
    """
    drafts: List[Dict[str, Any]] = []

    net = base_state.get("network_state", {})
    median_fee = int(net.get("txn_median_fee", 10) or 10)
    load_factor = float(net.get("load_factor", 1.0) or 1.0)

    drafts.append(
        {
            "id": str(uuid.uuid4()),
            "name": "anomaly_timeline_engine",
            "category": "analysis",
            "summary": "Build rolling anomaly timelines over fee / load / policy signals.",
            "inputs": ["network_state", "guardian", "fee_horizon"],
            "outputs": ["timeline", "anomaly_clusters"],
            "motivation": "Give operators a time-based view of when and why pressure appears.",
        }
    )

    drafts.append(
        {
            "id": str(uuid.uuid4()),
            "name": "rpc_reliability_estimator",
            "category": "infra",
            "summary": "Score XRPL RPC nodes by latency, error rate, and data consistency.",
            "inputs": ["xrpl_rpc_layer", "telemetry_core"],
            "outputs": ["node_scores", "fallback_plan"],
            "motivation": "Increase robustness of read-only observers and avoid noisy nodes.",
        }
    )

    drafts.append(
        {
            "id": str(uuid.uuid4()),
            "name": "mesh_bias_detector",
            "category": "meta",
            "summary": "Detect systematic biases in advice for wallets, integrators, and operators.",
            "inputs": ["mesh_intent", "guardian", "network_state"],
            "outputs": ["bias_report", "mitigation_suggestions"],
            "motivation": "Ensure balanced recommendations across user groups and flows.",
        }
    )

    drafts.append(
        {
            "id": str(uuid.uuid4()),
            "name": "fee_pressure_playbook_generator",
            "category": "playbook",
            "summary": "Generate human-readable playbooks for fee pressure modes.",
            "inputs": ["guardian", "fee_horizon", "tools"],
            "outputs": ["playbook_docs"],
            "motivation": "Make it trivial to operationalize AI advice into standard operating procedures.",
        }
    )

    # Example of condition-based extra draft
    if median_fee >= 5000 or load_factor > 2.0:
        drafts.append(
            {
                "id": str(uuid.uuid4()),
                "name": "pressure_resilience_simulator",
                "category": "simulation",
                "summary": "Offline simulator for infra reaction to sustained fee pressure.",
                "inputs": ["network_state", "scheduler", "fee_horizon"],
                "outputs": ["resilience_score", "bottleneck_report"],
                "motivation": "Understand how infra scales when pressure persists for hours/days.",
            }
        )

    return drafts


def assess_and_evolve(base_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Top-level entry point for the structural intelligence layer.

    Returns:
      {
        "structure": {
          "components": [...],
          "health": {...},
          "upgrade_suggestions": [...],
          "evolution_drafts": [...],
        },
        "ledger_entry": {...},
      }
    """
    components = _build_structural_map(base_state)
    health = _evaluate_health(components)
    upgrades = _plan_upgrades(components, health, base_state)
    drafts = _generate_evolution_drafts(components, health, base_state)

    now = datetime.now(timezone.utc).isoformat()
    infra_state = health.get("infra_state", "UNKNOWN")
    pipeline_version = base_state.get("pipeline_version")

    ledger_entry = {
        "id": str(uuid.uuid4()),
        "created_at": now,
        "infra_state": infra_state,
        "pipeline_version": pipeline_version,
        "components": [asdict(c) for c in components],
        "health": health,
        "upgrade_suggestions": upgrades,
        "evolution_drafts": drafts,
    }

    return {
        "structure": {
            "components": [asdict(c) for c in components],
            "health": health,
            "upgrade_suggestions": upgrades,
            "evolution_drafts": drafts,
        },
        "ledger_entry": ledger_entry,
    }
