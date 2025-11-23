"""
multileg_batcher.py
XRPL Quantum Batching Engine v2.0
Governor XRPL Quantum Lab
"""

from typing import Any, Dict, List

# Existing system components
from ecosystem.quantum_fusion import compute_quantum_signal
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.brain import tx_brain
from ecosystem.tx.router_v3 import TxRouterV3
from ecosystem.protocol_graph import ProtocolSelector, build_default_graph
from ecosystem.network import get_network_state

BATCHER_VERSION = "2.0.0"


class MultilegBatcher:
    """
    Takes multiple TxIntent objects and builds:
      - global quantum pressure profile
      - ordered execution bundle
      - batch fee profile
      - router priorities
      - unified execution window
    """

    def __init__(self):
        self._router = TxRouterV3()
        self._selector = ProtocolSelector(build_default_graph())

    # --------------------------------------------------------
    # QUANTUM AGGREGATION
    # --------------------------------------------------------
    def _aggregate_quantum(self, per_leg_q: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine per-leg quantum signals into global batch-level signal.
        """
        if not per_leg_q:
            return compute_quantum_signal({"txn_median_fee": 0})

        max_band = max(q["pressure_score"] for q in per_leg_q)
        avg_fee = sum(q["median_fee_drops"] for q in per_leg_q) / len(per_leg_q)
        avg_recommended = sum(q["recommended_fee_drops"] for q in per_leg_q) / len(per_leg_q)

        return {
            "version": BATCHER_VERSION,
            "pressure_score": max_band,
            "median_fee_drops": int(avg_fee),
            "recommended_fee_drops": int(avg_recommended),
            "safe_fee_drops": int(avg_recommended * 1.1),
            "band": "extreme" if max_band >= 0.85 else "elevated",
            "guardian_mode": "fee_pressure",
            "notes": ["Batch-aggregated quantum state"]
        }

    # --------------------------------------------------------
    def _order_legs(self, intents: List[TxIntent], quantum: Dict[str, Any]) -> List[TxIntent]:
        """
        Order legs by cost → risk → pressure logic.
        Lower cost and lower risk legs execute first.
        """
        return sorted(
            intents,
            key=lambda i: (
                i.amount_drops,
                len(i.metadata) if i.metadata else 0
            )
        )

    # --------------------------------------------------------
    def plan_batch(self, intents: List[TxIntent]) -> Dict[str, Any]:
        """
        Build a unified multileg batch plan.
        """

        # Network state
        net_state = get_network_state()

        # Compute per-leg quantum
        per_leg_q = [compute_quantum_signal(net_state) for _ in intents]

        # Batch-level quantum
        batch_quantum = self._aggregate_quantum(per_leg_q)

        # Order legs
        ordered_intents = self._order_legs(intents, batch_quantum)

        # Build per-leg tx_plans and router decisions
        plans = []
        for intent in ordered_intents:
            tx_plan = tx_brain.plan_for_intent(
                intent,
                net_state,
                guardian_hint=batch_quantum
            )

            router_res = self._router.route(
                intent.as_dict(),
                net_state,
                batch_quantum,
                tx_plan
            )

            plans.append({
                "intent": intent.as_dict(),
                "tx_plan": tx_plan,
                "router": router_res
            })

        # Build unified execution window
        execution_window = {
            "recommended_fee": batch_quantum["recommended_fee_drops"],
            "safe_fee": batch_quantum["safe_fee_drops"],
            "expected_ledger_span": "3-6 ledgers",
            "mode": "batched",
            "priority": "high" if batch_quantum["pressure_score"] >= 0.85 else "normal",
        }

        return {
            "version": BATCHER_VERSION,
            "batch_quantum": batch_quantum,
            "network_state": net_state,
            "execution_window": execution_window,
            "plans": plans
        }


# ------------------------------------------------------------
# STD CONSTRUCTOR
# ------------------------------------------------------------

def build_multileg_batcher() -> MultilegBatcher:
    return MultilegBatcher()
