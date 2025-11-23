"""
multileg.py — Governor XRPL Multi-Leg Engine (Mueller Fix Edition)
Correct routing: always pass TxIntent to RouterV3.
"""

from typing import Any, Dict, List
from ecosystem.tx.router_v3 import TxRouterV3
from ecosystem.tx.intents import TxIntent
from ecosystem.protocol_graph import ProtocolSelector
from ecosystem.network_state import get_network_state
from ecosystem.quantum_fusion import compute_quantum_signal
from ecosystem.tx.brain import tx_brain


class MultiLegEngine:
    VERSION = "2.0.0"

    def __init__(self):
        self._router = TxRouterV3()
        self._selector = ProtocolSelector()

    # ------------------------------------------------------------
    def plan_bundle(self, intents: List[TxIntent]) -> Dict[str, Any]:
        net = get_network_state()
        quantum = compute_quantum_signal(net)

        bundle = []

        for intent in intents:
            # Compute tx plan
            tx_plan = tx_brain.plan_for_intent(intent, net, quantum)

            # Mueller fix: pass TxIntent object directly
            route_sel = self._router.route(
                intent,
                net,
                quantum,
                tx_plan
            )

            bundle.append({
                "intent": intent.as_dict(),
                "selection": route_sel,
                "tx_plan": tx_plan
            })

        return {
            "version": self.VERSION,
            "band": quantum["band"],
            "guardian_mode": quantum["guardian_mode"],
            "risk_budget": 9,
            "plans": bundle
        }


def build_default_multileg_engine():
    return MultiLegEngine()



