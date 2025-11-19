"""
Level 5: Adaptive Scheduler for VQM Ecosystem.

Takes the projected fee horizon and produces a plan for various
"job classes" – indexers, analytics, batch settlements, experiments, etc.

This does *not* execute jobs. It only returns a schedule plan.
"""

from typing import Dict, Any, List


class AdaptiveScheduler:
    """
    Stateless scheduler: given (fee_horizon, network_state) it returns
    a recommended schedule plan – how aggressively each job class
    should run under current and projected conditions.
    """

    def __init__(self) -> None:
        # Policy knobs – tweakable without changing behavior shape.
        self._base_concurrency = {
            "indexer": 4,
            "analytics": 2,
            "batch_settlements": 2,
            "experiments": 1,
            "archival": 1,
        }

    def _policy_for_band(self, band: str) -> Dict[str, Dict[str, Any]]:
        """
        Map projected_fee_band -> per-job behavior.
        """
        band = band or "normal"

        if band == "low":
            # Network is cheap & calm: open throttle (a little).
            return {
                "indexer": {"mode": "aggressive", "multiplier": 1.5},
                "analytics": {"mode": "aggressive", "multiplier": 1.5},
                "batch_settlements": {"mode": "normal", "multiplier": 1.2},
                "experiments": {"mode": "normal", "multiplier": 1.5},
                "archival": {"mode": "normal", "multiplier": 1.3},
            }
        if band == "normal":
            return {
                "indexer": {"mode": "normal", "multiplier": 1.0},
                "analytics": {"mode": "normal", "multiplier": 1.0},
                "batch_settlements": {"mode": "normal", "multiplier": 1.0},
                "experiments": {"mode": "limited", "multiplier": 1.0},
                "archival": {"mode": "normal", "multiplier": 1.0},
            }
        if band == "elevated":
            return {
                "indexer": {"mode": "normal", "multiplier": 0.9},
                "analytics": {"mode": "limited", "multiplier": 0.7},
                "batch_settlements": {"mode": "prioritized", "multiplier": 1.0},
                "experiments": {"mode": "paused", "multiplier": 0.0},
                "archival": {"mode": "limited", "multiplier": 0.5},
            }
        if band == "extreme":
            return {
                "indexer": {"mode": "essential_only", "multiplier": 0.5},
                "analytics": {"mode": "paused", "multiplier": 0.0},
                "batch_settlements": {"mode": "essential_only", "multiplier": 0.8},
                "experiments": {"mode": "hard_paused", "multiplier": 0.0},
                "archival": {"mode": "paused", "multiplier": 0.0},
            }

        # Safe fallback
        return {
            "indexer": {"mode": "normal", "multiplier": 1.0},
            "analytics": {"mode": "normal", "multiplier": 1.0},
            "batch_settlements": {"mode": "normal", "multiplier": 1.0},
            "experiments": {"mode": "limited", "multiplier": 0.5},
            "archival": {"mode": "normal", "multiplier": 1.0},
        }

    def plan(self, fee_horizon: Dict[str, Any], network_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint:

        Returns:
            {
                "version": "0.1.0",
                "band": "normal|elevated|extreme|low|unknown",
                "jobs": [
                    {
                        "name": "indexer",
                        "base_concurrency": 4,
                        "target_concurrency": 4,
                        "mode": "normal",
                    },
                    ...
                ],
                "notes": "...",
            }
        """
        band = fee_horizon.get("projected_fee_band", "unknown")
        policy = self._policy_for_band(band)

        jobs: List[Dict[str, Any]] = []
        for name, base in self._base_concurrency.items():
            cfg = policy.get(name, {"mode": "normal", "multiplier": 1.0})
            target = int(round(base * float(cfg.get("multiplier", 1.0))))
            if target < 0:
                target = 0

            jobs.append(
                {
                    "name": name,
                    "base_concurrency": base,
                    "target_concurrency": target,
                    "mode": cfg.get("mode", "normal"),
                }
            )

        notes = f"Scheduler based on band='{band}' and current median_fee={network_state.get('txn_median_fee')}."

        return {
            "version": "0.1.0",
            "band": band,
            "jobs": jobs,
            "notes": notes,
        }
