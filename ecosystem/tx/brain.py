"""
ecosystem.tx.brain
------------------
Transaction Protocol Brain (Phase-E).

- Chooses protocol variant based on:
    * intent.kind
    * live network_state
    * guardian hints (fee_pressure, etc.)
- Still **read-only**: no signing, no submission.
"""

from typing import Dict, Any, Optional

from ecosystem.tx.intents import TxIntent
from ecosystem.tx import protocols


def _guardian_mode(guardian_hint: Optional[Dict[str, Any]]) -> str:
    if not guardian_hint:
        return "unknown"

    # try mesh.mode, then policy.mode, then top-level mode
    return (
        guardian_hint.get("mesh", {}).get("mode")
        or guardian_hint.get("policy", {}).get("mode")
        or guardian_hint.get("mode")
        or "unknown"
    )


class TransactionProtocolBrain:
    """
    Central protocol planner. Safe by design.
    """

    def plan_for_intent(
        self,
        intent: TxIntent,
        network_state: Dict[str, Any],
        guardian_hint: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        kind = intent.kind
        median = network_state["txn_median_fee"]
        guardian_mode = _guardian_mode(guardian_hint)

        # ---- Simple payments (v1 vs v2) ----
        if kind == "simple_payment":
            # If fees are hot or guardian says "fee_pressure", use v2 (safer)
            if median > 200 or guardian_mode in ("fee_pressure", "conserve_resources"):
                return protocols.simple_payment_v2(intent, network_state, guardian_hint)
            return protocols.simple_payment_v1(intent, network_state)

        # ---- Escrow milestone protocol ----
        if kind == "escrow_milestone":
            return protocols.escrow_milestone_v1(intent, network_state, guardian_hint)

        # ---- Streamed salary / subscriptions ----
        if kind == "streamed_salary":
            return protocols.streamed_salary_v1(intent, network_state, guardian_hint)

        # ---- Fallback for unknown kinds ----
        return {
            "protocol": "unknown",
            "intent_kind": kind,
            "network_state": network_state,
            "risk": {"level": 4, "reasons": ["unknown intent kind"]},
            "steps": [],
        }


tx_brain = TransactionProtocolBrain()



