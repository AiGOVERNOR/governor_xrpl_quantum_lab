"""
Level 6: Mesh Intent Router.

Compresses network_state + fee horizon + scheduler into a single
"intent" object describing how the VQM ecosystem *should* behave
right now. Still no signing, no trading – just guidance.
"""

from typing import Dict, Any


class MeshIntentRouter:
    """
    Stateless router that produces a high-level "ecosystem intent"
    for wallets, integrators, and node operators.
    """

    def __init__(self) -> None:
        self.version = "0.1.0"

    def route(
        self,
        network_state: Dict[str, Any],
        fee_horizon: Dict[str, Any],
        schedule: Dict[str, Any],
    ) -> Dict[str, Any]:
        band = fee_horizon.get("projected_fee_band", "unknown")
        trend = fee_horizon.get("trend_short", {}).get("direction", "flat")
        median_fee = network_state.get("txn_median_fee")
        load_factor = network_state.get("load_factor", 1.0)

        # High-level mode
        if band in ("extreme", "elevated"):
            mode = "protect_network"
            priority = "essential_flows_only"
        elif band == "low":
            mode = "explore_capacity"
            priority = "throughput_and_growth"
        else:
            mode = "steady_state"
            priority = "balanced"

        wallets_advice = []
        integrators_advice = []
        operators_advice = []

        if band in ("elevated", "extreme"):
            wallets_advice.append(
                "Prefer simple payments and avoid complex multi-hop paths during fee pressure."
            )
            integrators_advice.append(
                "Batch non-urgent payouts and avoid unnecessary on-chain churn."
            )
            operators_advice.append(
                "Monitor validator health and consider temporarily reducing non-essential workloads."
            )
        elif band == "low":
            wallets_advice.append("Network is calm – good moment for settlements and housekeeping.")
            integrators_advice.append(
                "Safe window for scheduled payouts and account maintenance."
            )
            operators_advice.append(
                "Use window to perform light maintenance and index catch-up."
            )
        else:
            wallets_advice.append("Operate normally with standard fee policies.")
            integrators_advice.append("Maintain normal flow; keep monitoring fee signals.")
            operators_advice.append("Keep usual monitoring and observability in place.")

        if trend == "rising":
            operators_advice.append("Fee trend is rising; be prepared for tighter policies.")
        elif trend == "falling":
            operators_advice.append("Fee trend is easing; you may relax temporary throttles soon.")

        return {
            "version": self.version,
            "mode": mode,
            "priority": priority,
            "inputs": {
                "band": band,
                "trend_short": trend,
                "median_fee": median_fee,
                "load_factor": load_factor,
            },
            "advice": {
                "wallets": wallets_advice,
                "integrators": integrators_advice,
                "node_operators": operators_advice,
            },
            "schedule_ref": {
                "band": schedule.get("band"),
                "job_count": len(schedule.get("jobs", [])),
            },
        }
