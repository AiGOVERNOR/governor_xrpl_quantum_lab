"""
VQM Mesh Autoscaler Helper
--------------------------
Reads the scheduler + band information from VQM state and
returns a suggested concurrency plan for jobs.

This does NOT mutate anything by itself; it's pure logic that
other systems can wire into their orchestration layer.
"""

from typing import Any, Dict, List


def _compute_scale_factor(band: str, base_factor: float = 1.0, max_scale: float = 3.0) -> float:
    """
    Very simple band-based multiplier:

    - low       => slightly below base
    - normal    => base
    - elevated  => modest bump
    - extreme   => larger bump (but capped)
    """
    band = (band or "normal").lower()

    factor = base_factor
    if band == "low":
        factor *= 0.75
    elif band == "normal":
        factor *= 1.0
    elif band == "elevated":
        factor *= 1.25
    elif band == "extreme":
        factor *= 1.5

    # Clamp
    if factor < 0.5:
        factor = 0.5
    if factor > max_scale:
        factor = max_scale

    return factor


def autoscale_from_state(state: Dict[str, Any], base_factor: float = 1.0, max_scale: float = 3.0) -> Dict[str, Any]:
    """
    Given a full VQM state (from /v1/state or run_vqm_cycle_v4),
    return a suggested concurrency plan for jobs.

    Expects a structure roughly like:

        state["scheduler"] = {
            "band": "normal",
            "jobs": [
                {"name": "indexer", "base_concurrency": 4, "mode": "normal"},
                ...
            ],
        }

    Returns:

        {
            "band": "...",
            "scale_factor": float,
            "jobs": [
                {
                    "name": "...",
                    "current_mode": "...",
                    "base_concurrency": int,
                    "suggested_concurrency": int,
                },
                ...
            ],
        }
    """
    scheduler = state.get("scheduler")
    if not scheduler:
        return {
            "enabled": False,
            "reason": "scheduler_missing",
        }

    band = scheduler.get("band", "normal")
    factor = _compute_scale_factor(band, base_factor=base_factor, max_scale=max_scale)

    jobs_plan: List[Dict[str, Any]] = []
    for job in scheduler.get("jobs", []):
        base = int(job.get("base_concurrency", 1))
        if base < 1:
            base = 1

        suggested = int(round(base * factor))
        if suggested < 1:
            suggested = 1

        jobs_plan.append(
            {
                "name": job.get("name"),
                "current_mode": job.get("mode"),
                "band": band,
                "base_concurrency": base,
                "suggested_concurrency": suggested,
            }
        )

    return {
        "enabled": True,
        "band": band,
        "scale_factor": factor,
        "jobs": jobs_plan,
    }
