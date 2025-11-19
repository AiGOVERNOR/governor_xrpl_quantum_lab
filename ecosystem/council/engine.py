from dataclasses import dataclass
from typing import Any, Dict, List, Literal


Band = Literal["low", "normal", "elevated", "extreme"]


@dataclass
class CouncilAgent:
    name: str
    role: str
    weight: float

    def vote(
        self,
        band: Band,
        load_factor: float,
        median_fee: int,
        horizon_comment: str,
    ) -> Dict[str, Any]:
        """
        Each agent returns a simple opinion object.

        This is intentionally transparent and rule-based so that you can
        later swap in more advanced logic without changing the envelope.
        """
        if band == "low":
            mode = "accelerate"
        elif band == "normal":
            mode = "steady_state"
        elif band == "elevated":
            mode = "fee_pressure"
        else:
            mode = "defensive"

        priority = "balanced"
        if band in ("elevated", "extreme"):
            priority = "safety_first"

        return {
            "agent": self.name,
            "role": self.role,
            "weight": self.weight,
            "band": band,
            "load_factor": load_factor,
            "median_fee": median_fee,
            "mode": mode,
            "priority": priority,
            "comment": horizon_comment,
        }


def _make_default_council() -> List[CouncilAgent]:
    return [
        CouncilAgent(name="InfraSentinel", role="infra", weight=0.4),
        CouncilAgent(name="LiquidityHermes", role="liquidity", weight=0.3),
        CouncilAgent(name="GuardianLex", role="policy", weight=0.2),
        CouncilAgent(name="IntegratorMuse", role="integrator", weight=0.1),
    ]


def _aggregate_votes(votes: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not votes:
        return {
            "mode": "steady_state",
            "priority": "balanced",
        }

    # Weighted majority logic
    mode_weights: Dict[str, float] = {}
    priority_weights: Dict[str, float] = {}

    for v in votes:
        w = float(v.get("weight", 1.0))
        mode = v.get("mode", "steady_state")
        prio = v.get("priority", "balanced")

        mode_weights[mode] = mode_weights.get(mode, 0.0) + w
        priority_weights[prio] = priority_weights.get(prio, 0.0) + w

    def _argmax(d: Dict[str, float]) -> str:
        return max(d.items(), key=lambda kv: kv[1])[0]

    mode = _argmax(mode_weights)
    priority = _argmax(priority_weights)

    return {
        "mode": mode,
        "priority": priority,
        "mode_weights": mode_weights,
        "priority_weights": priority_weights,
    }


def _build_scheduler(band: Band) -> Dict[str, Any]:
    """
    Simple, band-aware scheduler suggestion. This is purely advisory;
    it does not start or stop any real jobs.
    """
    # Base config
    base_jobs = [
        {"name": "indexer", "base_concurrency": 4},
        {"name": "analytics", "base_concurrency": 2},
        {"name": "batch_settlements", "base_concurrency": 2},
        {"name": "experiments", "base_concurrency": 1},
        {"name": "archival", "base_concurrency": 1},
    ]

    jobs_out: List[Dict[str, Any]] = []

    for job in base_jobs:
        base = job["base_concurrency"]
        name = job["name"]

        if band == "low":
            factor = 1.5
            mode = "aggressive" if name in ("indexer", "analytics") else "normal"
        elif band == "normal":
            factor = 1.0
            mode = "normal"
        elif band == "elevated":
            factor = 0.8
            mode = "limited" if name == "experiments" else "normal"
        else:  # extreme
            factor = 0.5
            mode = "limited"

        target = max(1, int(round(base * factor)))
        jobs_out.append(
            {
                "name": name,
                "base_concurrency": base,
                "target_concurrency": target,
                "mode": mode,
            }
        )

    notes = f"Scheduler tuned for band='{band}'."

    return {
        "band": band,
        "jobs": jobs_out,
        "notes": notes,
        "version": "0.2.0",
    }


def build_council_decision(
    network_state: Dict[str, Any],
    fee_horizon: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Main entry point for the Council/Super-brain.

    Returns:
      {
        "council": {...},
        "mesh_intent": {...},
        "scheduler": {...},
      }
    """
    band: Band = fee_horizon.get("projected_fee_band", "normal")  # type: ignore
    load_factor = float(network_state.get("load_factor", 1.0))
    median_fee = int(network_state.get("txn_median_fee", 10))
    comment = fee_horizon.get("comment", "")

    council = _make_default_council()
    votes = [
        a.vote(
            band=band,
            load_factor=load_factor,
            median_fee=median_fee,
            horizon_comment=comment,
        )
        for a in council
    ]

    aggregate = _aggregate_votes(votes)
    scheduler = _build_scheduler(band)

    mesh_intent = {
        "version": "0.2.0",
        "mode": aggregate["mode"],
        "priority": aggregate["priority"],
        "inputs": {
            "band": band,
            "median_fee": median_fee,
            "load_factor": load_factor,
            "trend_short": fee_horizon.get("trend_short", {}).get("direction"),
        },
        "advice": {
            "wallets": [
                "Operate within usual fee envelopes; avoid unnecessary complexity."
            ]
            if band in ("low", "normal")
            else [
                "Prefer simpler payments over complex paths; surface fee estimates "
                "clearly to users."
            ],
            "integrators": [
                "Design flows assuming current band and watch fee horizon."
            ],
            "node_operators": [
                "Monitor health, consider raising observability on XRPL RPC latency."
            ],
        },
        "schedule_ref": {
            "band": scheduler["band"],
            "job_count": len(scheduler["jobs"]),
        },
    }

    council_state = {
        "version": "0.1.0",
        "band": band,
        "load_factor": load_factor,
        "median_fee": median_fee,
        "votes": votes,
        "aggregate": aggregate,
    }

    return {
        "council": council_state,
        "mesh_intent": mesh_intent,
        "scheduler": scheduler,
    }
