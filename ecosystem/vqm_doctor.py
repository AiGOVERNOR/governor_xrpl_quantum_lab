# ecosystem/vqm_doctor.py

"""
VQM Doctor
----------
Meta-diagnostics for the Governor XRPL Quantum Lab.

This module:
- Runs small self-tests against key subsystems:
  * tx_brain (TransactionProtocolBrain)
  * TxRouterV3
  * Protocol graph selector
  * FlowEngine (CPFE)
  * MultiLegEngine
  * SDK client
  * Execution planner

- Returns a JSON-friendly dict:
  {
    "tx_brain": {"ok": True, "details": {...}} or {"ok": False, "error": "..."},
    "router_v3": {...},
    ...
  }

Nothing here touches keys, signs, or trades. It’s read-only planning + introspection.
"""

from typing import Any, Dict


def _safe_result(name: str, fn) -> Dict[str, Any]:
    try:
        details = fn()
        return {"ok": True, "details": details}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _check_tx_brain() -> Dict[str, Any]:
    from ecosystem.tx.intents import TxIntent
    from ecosystem.tx.brain import tx_brain

    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_DOCTOR",
        destination_account="rDEST_DOCTOR",
        metadata={"note": "doctor_tx_brain"},
    )

    # Let the brain / pipeline decide network_state via pipeline_v5
    # We just feed it a placeholder network_state; your current brain ignores/overrides it.
    net_state = {
        "txn_median_fee": 5_000,
        "recommended_fee_drops": 5_000,
        "load_factor": 1.0,
    }

    plan = tx_brain.plan_for_intent(intent, net_state, guardian_hint=None)
    return {
        "intent_kind": intent.kind,
        "protocol": plan.get("protocol"),
        "risk": plan.get("risk"),
        "network_state": plan.get("network_state"),
    }


def _check_router_v3() -> Dict[str, Any]:
    from ecosystem.tx.intents import TxIntent
    from ecosystem.tx.router_v3 import TxRouterV3
    from ecosystem.tx.brain import tx_brain

    router = TxRouterV3()

    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_ROUTER",
        destination_account="rDEST_ROUTER",
        metadata={"note": "doctor_router"},
    )

    # Reuse tx_brain to get a proper plan + state
    net_state_hint = {
        "txn_median_fee": 5_000,
        "recommended_fee_drops": 5_000,
        "load_factor": 1.0,
    }
    tx_plan = tx_brain.plan_for_intent(intent, net_state_hint, guardian_hint=None)
    net_state = tx_plan.get("network_state", net_state_hint)

    decision = router.route(
        intent=intent,
        network_state=net_state,
        guardian_hint=None,
        tx_plan=tx_plan,
    )

    return {
        "selected_protocol": decision.get("selected", {}).get("protocol"),
        "band": decision.get("meta", {}).get("band"),
        "guardian_mode": decision.get("meta", {}).get("guardian_mode"),
        "score": decision.get("selected", {}).get("score"),
    }


def _check_protocol_graph() -> Dict[str, Any]:
    from ecosystem.protocol_graph import build_default_graph, ProtocolSelector

    graph = build_default_graph()
    selector = ProtocolSelector(graph)

    decision = selector.select_for_intent(
        intent_kind="simple_payment",
        median_fee=5_000,
        recommended_fee=5_000,
        band="extreme",
    )

    return decision


def _check_flow_engine() -> Dict[str, Any]:
    from ecosystem.flow_engine import build_default_flow_engine
    from ecosystem.tx.intents import TxIntent

    engine = build_default_flow_engine()

    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_FLOW",
        destination_account="rDEST_FLOW",
        metadata={"note": "doctor_flow"},
    )

    decision = engine.plan_flow(intent)

    return {
        "engine_version": decision.get("engine_version"),
        "band": decision.get("quantum", {}).get("band"),
        "router_protocol": decision.get("router_decision", {})
        .get("selected", {})
        .get("protocol"),
    }


def _check_multileg() -> Dict[str, Any]:
    from ecosystem.multileg import build_default_multileg_engine
    from ecosystem.tx.intents import TxIntent

    engine = build_default_multileg_engine()

    intents = [
        TxIntent.new(
            kind="simple_payment",
            amount_drops=1_000_000,
            source_account="rSOURCE_MULTI_1",
            destination_account="rDEST_MULTI_1",
            metadata={"memo": "leg1"},
        ),
        TxIntent.new(
            kind="simple_payment",
            amount_drops=2_000_000,
            source_account="rSOURCE_MULTI_2",
            destination_account="rDEST_MULTI_2",
            metadata={"memo": "leg2"},
        ),
    ]

    bundle = engine.plan_bundle(intents)

    return {
        "version": bundle.get("version"),
        "band": bundle.get("quantum", {}).get("band"),
        "legs": len(bundle.get("results", [])),
    }


def _check_sdk_client() -> Dict[str, Any]:
    from ecosystem.sdk.client import VQMClient

    client = VQMClient()

    decision = client.simple_payment(
        amount_drops=1_000_000,
        source_account="rSOURCE_SDK",
        destination_account="rDEST_SDK",
        memo="sdk_doctor",
    )

    return {
        "engine_version": decision.get("engine_version"),
        "router_protocol": decision.get("router_decision", {})
        .get("selected", {})
        .get("protocol"),
        "scheduler_band": decision.get("scheduler_band"),
    }


def _check_execution() -> Dict[str, Any]:
    from ecosystem.execution import plan_execution
    from ecosystem.tx.intents import TxIntent

    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_EXEC",
        destination_account="rDEST_EXEC",
        metadata={"note": "exec_doctor"},
    )

    result = plan_execution(intent)

    return {
        "execution_version": result.get("execution_version"),
        "recommended_mode": result.get("execution_hint", {}).get(
            "recommended_mode"
        ),
        "urgency": result.get("execution_hint", {}).get("urgency"),
        "safe_fee_drops": result.get("fee", {}).get("safe_fee_drops"),
    }


def run_all_checks() -> Dict[str, Any]:
    """
    Run all subsystem checks and return a single structured report.
    """

    return {
        "tx_brain": _safe_result("tx_brain", _check_tx_brain),
        "router_v3": _safe_result("router_v3", _check_router_v3),
        "protocol_graph": _safe_result("protocol_graph", _check_protocol_graph),
        "flow_engine": _safe_result("flow_engine", _check_flow_engine),
        "multileg": _safe_result("multileg", _check_multileg),
        "sdk_client": _safe_result("sdk_client", _check_sdk_client),
        "execution": _safe_result("execution", _check_execution),
    }
