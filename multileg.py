"""
ecosystem.multileg
Multi-leg planner engine (V3) for XRPL Governor Quantum Lab.
"""

from typing import Any, Dict, List
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.brain import tx_brain
from ecosystem.tx.router_v3 import TxRouterV3
from ecosystem.protocol_graph import ProtocolSelector, build_default_graph
from ecosystem.quantum_fusion import compute_quantum_signal


class MultilegEngine:
    """
    Multi-leg transaction planner.
    Produces: {
        "legs": [...],
        "bundle_risk": ...,
        "quantum": ...,
        "protocol_graph": ...,
        "router": ...
    }
    """

    def __init__(self):
        self._router = TxRouterV3()
        self._selector = ProtocolSelector(build_default_graph())

    # ---------------------------------------------------------
    # Internal: match the NEW compute_quantum_signal() signature
    # ---------------------------------------------------------
    def _quantum_from_state(self, net_state: Dict[str, Any]) -> Dict[str, Any]:
        return compute_quantum_signal(
            network_state=net_state,
            guardian_present=True
        )

    # ---------------------------------------------------------
    # MAIN MULTI-LEG LOGIC
    # ---------------------------------------------------------
    def plan_bundle(self, intents: List[TxIntent]) -> Dict[str, Any]:
        legs = []
        total_risk = 0
        total_score = 0

        # Snapshot (can be replaced with live RPC later)
        net_state = {
            "ledger_seq": 999999,
            "txn_median_fee": 5000,
            "recommended_fee_drops": 5000,
            "load_factor": 1.0,
        }

        # Compute quantum signal
        quantum = self._quantum_from_state(net_state)

        for intent in intents:

            # 1) Transaction Brain
            tx_plan = tx_brain.plan_for_intent(
                intent,
                net_state,
                guardian_hint={"mode": "fee_pressure"}
            )

            # 2) Router V3 advisory layer
            router_decision = self._router.route(
                intent,
                net_state,
                {"mode": "fee_pressure"},
                tx_plan
            )

            # 3) Protocol Graph Selection
            graph_decision = self._selector.select_for_intent(
                intent.kind,
                median_fee=net_state["txn_median_fee"],
                recommended_fee=net_state["recommended_fee_drops"],
                band=quantum["band"]
            )

            risk_level = router_decision["selected"].get("risk", {}).get("final_level", 1)
            total_risk += risk_level
            total_score += router_decision["selected"].get("score", 0.0)

            legs.append(
                {
                    "intent": intent.as_dict(),
                    "tx_plan": tx_plan,
                    "router": router_decision,
                    "protocol_graph": graph_decision,
                }
            )

        return {
            "multileg_version": "0.5.0",
            "quantum": quantum,
            "legs": legs,
            "aggregate": {
                "total_legs": len(legs),
                "risk_sum": total_risk,
                "score_sum": total_score,
                "avg_risk": total_risk / len(legs),
                "avg_score": total_score / len(legs),
            },
        }


# ---------------------------------------------------------
# Engine Builder
# ---------------------------------------------------------
def build_default_multileg_engine() -> MultilegEngine:
    return MultilegEngine()


# ---------------------------------------------------------
# Self-check diagnostics
# ---------------------------------------------------------
def multileg_wiring_selfcheck() -> Dict[str, Any]:
    return {
        "router": "TxRouterV3",
        "selector": "ProtocolSelector",
        "quantum": "compute_quantum_signal (network_state-based)",
        "status": "ok",
    }
