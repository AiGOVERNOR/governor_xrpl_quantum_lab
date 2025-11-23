from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from .loader import load_profit_agent_config, AGENT_CODE_VERSION

# We only depend on the public builder used by the existing CLI.
from ecosystem.flow_engine import build_default_flow_engine


def build_probe_intent() -> Dict[str, Any]:
    """
    Simple probe intent used to ask the engine:
    'Is the network currently cheap and calm enough to act?'
    """
    return {
        "kind": "simple_payment",
        "amount_drops": 1_000_000,
        "source_account": "rSOURCE_ACCOUNT_PLACEHOLDER",
        "destination_account": "rDESTINATION_ACCOUNT_PLACEHOLDER",
        "metadata": {
            "memo": "profit_agent_probe"
        },
    }


def evaluate_triggers(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a minimal view of network conditions from a flow_engine
    decision bundle.
    """
    net = decision.get("network_state", {}) or {}
    quantum = decision.get("quantum", {}) or {}

    median_fee = float(net.get("txn_median_fee", 0))
    load_factor = float(net.get("load_factor", 0.0))
    band = str(quantum.get("band", "unknown"))
    guardian_mode = str(quantum.get("guardian_mode", "unknown"))

    return {
        "median_fee": median_fee,
        "load_factor": load_factor,
        "band": band,
        "guardian_mode": guardian_mode,
    }


def should_execute(trig_view: Dict[str, Any], cfg_obj) -> tuple[bool, str]:
    """
    Decide whether the agent is allowed to act, based on current
    network conditions and the agent's trigger + constraint config.
    """
    t = cfg_obj.trigger
    c = cfg_obj.constraints

    median_fee = trig_view["median_fee"]
    load_factor = trig_view["load_factor"]

    reasons = []

    if median_fee <= t.median_fee_max:
        reasons.append(f"median_fee_ok({median_fee} <= {t.median_fee_max})")
        fee_ok = True
    else:
        reasons.append(f"median_fee_high({median_fee} > {t.median_fee_max})")
        fee_ok = False

    if load_factor <= t.max_load_factor:
        reasons.append(f"load_ok({load_factor} <= {t.max_load_factor})")
        load_ok = True
    else:
        reasons.append(f"load_high({load_factor} > {t.max_load_factor})")
        load_ok = False

    risk_ok = c.max_risk_level <= 2
    if risk_ok:
        reasons.append(f"risk_budget_ok({c.max_risk_level} <= 2)")
    else:
        reasons.append(f"risk_budget_exceeded({c.max_risk_level} > 2)")

    allowed = fee_ok and load_ok and risk_ok

    if allowed:
        summary = " & ".join(reasons)
    else:
        summary = "BLOCKED: " + " & ".join(reasons)

    return allowed, summary


def build_agent_summary(decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compact human-readable summary similar to the existing CLIs.
    """
    intent = decision.get("intent") or {}
    quantum = decision.get("quantum") or {}

    return {
        "intent_kind": intent.get("kind"),
        "amount_drops": intent.get("amount_drops"),
        "band": quantum.get("band"),
        "guardian_mode": quantum.get("guardian_mode"),
        "recommended_fee_drops": quantum.get("recommended_fee_drops"),
        "safe_fee_drops": quantum.get("safe_fee_drops"),
    }


def main() -> None:
    """
    Entry point for the profit agent. Safe-by-design:

    - Read-only: we only ask the flow engine for advice.
    - No signing, no submission, no private keys.
    - Self-healing config loader keeps the JSON sane.
    """
    started_at = datetime.utcnow().isoformat() + "Z"

    try:
        cfg = load_profit_agent_config()
    except Exception as exc:  # pragma: no cover - defensive
        result = {
            "agent_version": AGENT_CODE_VERSION,
            "started_at": started_at,
            "ok": False,
            "error": f"failed_to_load_config: {exc!r}",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    intent = build_probe_intent()
    engine = build_default_flow_engine()

    try:
        decision = engine.plan_flow(intent)
    except Exception as exc:  # pragma: no cover - defensive
        result = {
            "agent_version": AGENT_CODE_VERSION,
            "started_at": started_at,
            "ok": False,
            "error": f"engine_plan_failed: {exc!r}",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    trig_view = evaluate_triggers(decision)
    allowed, reason = should_execute(trig_view, cfg)
    summary = build_agent_summary(decision)

    result = {
        "agent_version": AGENT_CODE_VERSION,
        "started_at": started_at,
        "ok": True,
        "config": cfg.to_dict(),
        "network_view": trig_view,
        "agent_summary": summary,
        "decision_preview": {
            "router_protocol": decision.get("router_decision", {}).get("protocol"),
            "execution_band": summary.get("band"),
        },
        "execution_intent": {
            "should_execute": allowed and cfg.action.execute_only_if_profitable,
            "allowed_by_triggers": allowed,
            "reason": reason,
            "mode": cfg.action.mode,
            "protocols": cfg.action.protocols,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
