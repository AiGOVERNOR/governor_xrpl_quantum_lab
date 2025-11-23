"""
protocol_selector.py
Governor XRPL Quantum Lab — Implementation Layer (v2.0)

This file implements an official ProtocolSelector that follows the
canonical contract defined in protocol_selector_contract.py.

It automatically:
 - selects appropriate protocol based on fee conditions
 - enforces risk_budget and guardian_mode constraints
 - self-corrects malformed inputs
 - guarantees contract-compliant output for the entire ecosystem
"""

from typing import Dict, Any
from .protocol_selector_contract import (
    ProtocolSelectorContract,
    PROTOCOL_SELECTOR_VERSION,
)


class ProtocolSelector(ProtocolSelectorContract):
    """
    Primary implementation used by:
      - flow_engine
      - tx_router_v3
      - multileg engine
      - vqm_doctor
      - sdk_client
    """

    def __init__(self):
        # weighted protocol table with dynamic selection logic
        self._protocols = {
            "simple_payment_v1": {
                "kind": "payment",
                "risk": 1,
                "tags": ["baseline", "cheap"]
            },
            "simple_payment_v2": {
                "kind": "payment",
                "risk": 2,
                "tags": ["dynamic_fee", "safer"]
            },
            "stream_pay_v1": {
                "kind": "stream",
                "risk": 3,
                "tags": ["salary", "subscription"]
            },
            "escrow_milestone_v1": {
                "kind": "escrow",
                "risk": 3,
                "tags": ["milestone", "project"]
            }
        }

    # ---------------------------------------------------------
    # REQUIRED BY CONTRACT
    # ---------------------------------------------------------
    def select_for_intent(
        self,
        intent_kind: str,
        median_fee: int,
        recommended_fee: int,
        guardian_mode: str,
        risk_budget: int
    ) -> Dict[str, Any]:

        # --- input sanitation --------------------------------
        guardian_mode = guardian_mode or "unknown"
        if risk_budget <= 0:
            risk_budget = 1

        # normalize intent
        intent_kind = str(intent_kind or "").lower().strip()

        # select candidate pool
        candidates = []
        for name, meta in self._protocols.items():
            if intent_kind in meta["kind"]:
                candidates.append((name, meta))

        # fallback to payment protocols if nothing matched
        if not candidates:
            candidates = [
                ("simple_payment_v1", self._protocols["simple_payment_v1"]),
                ("simple_payment_v2", self._protocols["simple_payment_v2"]),
            ]

        # compute selection score
        best = None
        best_score = -1.0
        for name, meta in candidates:
            risk = meta["risk"]

            # skip protocols exceeding risk budget
            if risk > risk_budget:
                continue

            # heuristic scoring
            score = 1.0 / (1.0 + abs(risk - risk_budget))

            # guardian mode penalty
            if guardian_mode == "fee_pressure" and risk > 1:
                score *= 0.7

            # fee escalation awareness
            if median_fee > recommended_fee:
                score *= 0.85

            if score > best_score:
                best_score = score
                best = (name, risk)

        if best is None:
            # fallback: always safe
            best = ("simple_payment_v1", 1)
            best_score = 0.5

        protocol_name, risk_level = best

        result = {
            "protocol": protocol_name,
            "risk_level": risk_level,
            "score": round(best_score, 4),
            "reason": (
                f"intent={intent_kind}; "
                f"band=inferred; "
                f"guardian={guardian_mode}; "
                f"risk={risk_level}"
            ),
            "version": PROTOCOL_SELECTOR_VERSION
        }

        # validate against contract to ensure full ecosystem stability
        ProtocolSelectorContract.validate_output(result)

        return result


# ---------------------------------------------------------
# Factory
# ---------------------------------------------------------
def build_default_protocol_selector() -> ProtocolSelector:
    """
    Flow engine, multileg, router_v3, and SDK use this factory.
    """
    return ProtocolSelector()
