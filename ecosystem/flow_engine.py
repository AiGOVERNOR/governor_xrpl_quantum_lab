"""
flow_engine.py — Governor XRPL FlowEngine (Mueller Fix Edition)
Ensures router receives TxIntent, not dict.
"""

from typing import Any, Dict, List, Union
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.router_v3 import TxRouterV3
from ecosystem.protocol_graph import ProtocolSelector
from ecosystem.network_state import get_network_state
from ecosystem.quantum_fusion import compute_quantum_signal


class FlowEngine:
    VERSION = "2.0.0"

    def __init__(self):
        self._router = TxRouterV3()
        self._selector = ProtocolSelector()

    # ------------------------------------------------------------
    def plan_flow(self, intent: Union[TxIntent, List[TxIntent]]) -> Dict[str, Any]:
        if isinstance(intent, list):
            return self._plan_batch(intent)
        return self._plan_single(intent)

    # ------------------------------------------------------------
    def _plan_single(self, intent: TxIntent) -> Dict[str, Any]:
        # Real-time XRPL network data
        net_state = get_network_state()

        # Compute quantum network signal
        quantum = compute_quantum_signal(net_state)

        # Select best protocol for this intent
        graph_sel = self._selector.select_for_intent(
            intent.kind,
            quantum["band"],
            quantum["guardian_mode"],
            risk_budget=9
        )

        # Build tx plan
        tx_plan = {
            "intent_kind": intent.kind,
            "network_state": net_state,
            "protocol": graph_sel["protocol"],
            "risk": {
                "level": 2,
                "reasons": [
                    "dynamic_fee",
                    "safety_buffer",
                    "median_fee_based"
                ]
            },
            "steps": [
                {"name": "check_accounts", "details": {
                    "source": intent.source_account,
                    "destination": intent.destination_account
                }},
                {"name": "estimate_fee_with_buffer", "details": {
                    "median_fee": net_state["txn_median_fee"],
                    "recommended_fee": net_state["recommended_fee_drops"],
                    "safe_fee": net_state["recommended_fee_drops"] + 500
                }},
                {"name": "prepare_payment_instruction", "details": {
                    "amount_drops": intent.amount_drops
                }}
            ]
        }

        # FIX: Pass TxIntent object directly (Mueller fix)
        route_sel = self._router.route(
            intent,      # ← NOT intent.as_dict()
            net_state,
            quantum,
            tx_plan
        )

        return {
            "engine_version": self.VERSION,
            "router_decision": route_sel,
            "intent": intent.as_dict(),
            "tx_plan": tx_plan,
            "quantum": quantum,
            "network_state": net_state
        }

    # ------------------------------------------------------------
    def _plan_batch(self, intents: List[TxIntent]) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "batch_count": len(intents),
            "plans": [self._plan_single(i) for i in intents]
        }


def build_default_flow_engine():
    return FlowEngine()
