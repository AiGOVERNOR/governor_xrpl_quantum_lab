"""
ecosystem.scheduler
-------------------
Simple, deterministic scheduler for VQM pipeline v5.

Takes:
  - fee band
  - median fee
  - load factor

Returns:
  - recommended concurrency levels for internal subsystems.

SAFE. No signing. No network mutation.
"""

from __future__ import annotations

from typing import Any, Dict


class Scheduler:
    """
    Very small policy scheduler.

    Modes:
      - low:      cheap network → increase concurrency
      - normal:   typical load → default values
      - elevated: busier → reduce heavy jobs
      - extreme:  high load → only essential jobs
    """

    def __init__(self) -> None:
        # All defaults
        self.defaults = {
            "indexer": 4,
            "analytics": 2,
            "batch_settlements": 2,
            "experiments": 1,
            "archival": 1,
        }

    def plan(self, band: str, median_fee: int, load_factor: float) -> Dict[str, Any]:
        """
        Return a stable scheduler block.
        """

        # Base concurrency for all jobs
        cfg = dict(self.defaults)

        # Modify based on fee band
        if band == "low":
            cfg["indexer"] = 6
            cfg["analytics"] = 3
            cfg["batch_settlements"] = 3
            cfg["experiments"] = 2

        elif band == "normal":
            pass  # keep defaults

        elif band == "elevated":
            cfg["analytics"] = 1
            cfg["batch_settlements"] = 1

        elif band == "extreme":
            # Minimal survival mode
            cfg = {
                "indexer": 1,
                "analytics": 0,
                "batch_settlements": 0,
                "experiments": 0,
                "archival": 0,
            }

        jobs = []
        for name, concurrency in cfg.items():
            jobs.append({
                "name": name,
                "base_concurrency": self.defaults.get(name, concurrency),
                "target_concurrency": concurrency,
                "mode": band,
            })

        return {
            "version": "0.2.0",
            "band": band,
            "jobs": jobs,
            "notes": f"Scheduled using band='{band}', median_fee={median_fee}, load={load_factor}",
        }
