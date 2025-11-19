from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from ecosystem.pipeline_v4 import run_vqm_cycle_v4 as base_run_vqm_cycle
from ecosystem.structure import assess_and_evolve
from ecosystem.structure.ledger import append_ledger_entry


def run_vqm_cycle_v5() -> Dict[str, Any]:
    """
    Wraps pipeline_v4 with structural intelligence:

    - Calls the existing VQM pipeline (v4)
    - Builds a structural map + health + upgrade suggestions
    - Appends a structural ledger entry
    - Returns a merged state with 'structure_state' attached
    """
    base_state: Dict[str, Any] = base_run_vqm_cycle()

    struct = assess_and_evolve(base_state)
    ledger_entry = struct.get("ledger_entry")

    if ledger_entry:
        try:
            append_ledger_entry(ledger_entry)
        except Exception:
            # Never break the main pipeline because of ledger issues
            pass

    merged = dict(base_state)
    merged["structure_state"] = struct["structure"]
    merged["pipeline_version"] = "2.0.0"

    meta = merged.setdefault("meta", {})
    meta["vqm_structure_version"] = "1.0.0"
    meta["last_structure_update_at"] = datetime.now(timezone.utc).isoformat()

    return merged
