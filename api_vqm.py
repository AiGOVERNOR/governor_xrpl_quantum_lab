from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ecosystem.pipeline_v5 import run_vqm_cycle_v5
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.brain import tx_brain
from ecosystem.tx.router_v3 import route_intent_v3


app = FastAPI(
    title="Governor VQM API",
    description=(
        "Read-only XRPL VQM brain. Streams network-aware policy, guardian output, "
        "fee bands, scheduler advice, and transaction protocol plans. "
        "No signing, no trading."
    ),
    version="1.1.0",
)


# -------------------------------------------------------------------
# Basic health + core state endpoints
# -------------------------------------------------------------------


@app.get("/health")
def health() -> Dict[str, Any]:
    """
    Simple liveness + pipeline wiring check.
    """
    return {"status": "ok", "component": "VQM-API", "version": app.version}


@app.get("/v1/state")
def get_state() -> Dict[str, Any]:
    """
    Full VQM state. This is the core API call.
    """
    return run_vqm_cycle_v5()


@app.get("/v1/guardian")
def get_guardian() -> Dict[str, Any]:
    """
    Guardian block: policy, forge, mesh, llm.
    """
    state = run_vqm_cycle_v5()
    guardian = state.get("guardian")
    if guardian is None:
        raise HTTPException(status_code=404, detail="Guardian block not present")
    return guardian


@app.get("/v1/tools")
def get_tools() -> Dict[str, Any]:
    """
    Tools registry: list of tools with scores and metadata.
    """
    state = run_vqm_cycle_v5()
    tools = state.get("tools", [])
    return {"tools": tools}


@app.get("/v1/fee-horizon")
def get_fee_horizon() -> Dict[str, Any]:
    """
    Optional: fee horizon / trends block if the pipeline exposes it.

    Returns 404 if the upstream has no 'fee_horizon' key.
    """
    state = run_vqm_cycle_v5()
    horizon = state.get("fee_horizon")
    if horizon is None:
        raise HTTPException(status_code=404, detail="fee_horizon not available")
    return horizon


@app.get("/v1/scheduler")
def get_scheduler() -> Dict[str, Any]:
    """
    Optional: scheduler advice block.

    Returns 404 if missing.
    """
    state = run_vqm_cycle_v5()
    scheduler = state.get("scheduler")
    if scheduler is None:
        raise HTTPException(status_code=404, detail="scheduler not available")
    return scheduler


# -------------------------------------------------------------------
# Human-friendly XRPL / VQM summary
# -------------------------------------------------------------------


@app.get("/vqm/summary")
def vqm_summary() -> Dict[str, Any]:
    """
    High-level summary of XRPL + VQM brain state.

    This is meant for dashboards, operators, and "is everything sane?"
    checks — not low-level bots.
    """
    state = run_vqm_cycle_v5()

    network = state.get("network_state", {}) or {}
    guardian = state.get("guardian", {}) or {}
    fee_horizon = state.get("fee_horizon")
    scheduler = state.get("scheduler")

    guardian_policy = guardian.get("policy", {})
    guardian_mode = guardian_policy.get("mode") or guardian.get("mesh", {}).get("mode")

    summary: Dict[str, Any] = {
        "ledger_seq": network.get("ledger_seq"),
        "fees": {
            "txn_base_fee": network.get("txn_base_fee"),
            "txn_median_fee": network.get("txn_median_fee"),
            "recommended_fee_drops": network.get("recommended_fee_drops"),
        },
        "load_factor": network.get("load_factor"),
        "guardian_mode": guardian_mode,
        "pipeline_version": state.get("pipeline_version"),
        "timestamp": state.get("timestamp"),
    }

    if fee_horizon is not None:
        summary["fee_horizon"] = {
            "band": fee_horizon.get("projected_fee_band"),
            "short_trend": fee_horizon.get("trend_short", {}).get("direction"),
            "long_trend": fee_horizon.get("trend_long", {}).get("direction"),
            "comment": fee_horizon.get("comment"),
        }

    if scheduler is not None:
        jobs = scheduler.get("jobs", [])
        summary["scheduler"] = {
            "band": scheduler.get("band"),
            "job_count": len(jobs),
        }

    return summary


# -------------------------------------------------------------------
# Transaction Brain V2 – API surface
#   These endpoints are ADVISORY ONLY.
#   They plan and route protocols; they DO NOT sign or submit.
# -------------------------------------------------------------------


class TxIntentPayload(BaseModel):
    """
    Minimal transaction intent payload for the API.

    This mirrors ecosystem.tx.intents.TxIntent.new(...) inputs
    for simple payments.
    """
    kind: str = "simple_payment"
    amount_drops: int
    source_account: str
    destination_account: str
    metadata: Optional[Dict[str, Any]] = None


@app.post("/v1/tx/plan")
def plan_transaction(payload: TxIntentPayload) -> Dict[str, Any]:
    """
    Plan a transaction protocol for the given intent using TransactionProtocolBrain V2.

    Returns:
      - echo of the intent
      - network_state used for planning
      - protocol plan (protocol name, steps, risk)
    """
    state = run_vqm_cycle_v5()
    network_state = state.get("network_state", {}) or {}
    guardian_hint = state.get("guardian")

    intent = TxIntent.new(
        kind=payload.kind,
        amount_drops=payload.amount_drops,
        source_account=payload.source_account,
        destination_account=payload.destination_account,
        metadata=payload.metadata or {},
    )

    plan = tx_brain.plan_for_intent(intent, network_state, guardian_hint)

    return {
        "intent": {
            "kind": payload.kind,
            "amount_drops": payload.amount_drops,
            "source_account": payload.source_account,
            "destination_account": payload.destination_account,
            "metadata": payload.metadata or {},
        },
        "network_state": network_state,
        "protocol_plan": plan,
    }


@app.post("/v1/tx/route")
def route_transaction(payload: TxIntentPayload) -> Dict[str, Any]:
    """
    Route a transaction intent using Router V3, on top of TransactionProtocolBrain V2.

    This endpoint:
      - reads live VQM state
      - plans a protocol via tx_brain
      - feeds that + network_state + guardian into router_v3
      - returns the route decision (still advisory-only)
    """
    state = run_vqm_cycle_v5()
    network_state = state.get("network_state", {}) or {}
    guardian_hint = state.get("guardian")

    intent = TxIntent.new(
        kind=payload.kind,
        amount_drops=payload.amount_drops,
        source_account=payload.source_account,
        destination_account=payload.destination_account,
        metadata=payload.metadata or {},
    )

    protocol_plan = tx_brain.plan_for_intent(intent, network_state, guardian_hint)

    route_decision = route_intent_v3(
        intent=intent,
        protocol_plan=protocol_plan,
        network_state=network_state,
        guardian_hint=guardian_hint,
    )

    return {
        "intent": {
            "kind": payload.kind,
            "amount_drops": payload.amount_drops,
            "source_account": payload.source_account,
            "destination_account": payload.destination_account,
            "metadata": payload.metadata or {},
        },
        "network_state": network_state,
        "protocol_plan": protocol_plan,
        "route_decision": route_decision,
    }
