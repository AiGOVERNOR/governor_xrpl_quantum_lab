"""
Single entrypoint for the VQM Ecosystem.

Used by:
- API layer
- CLI
- future automation hooks
"""

from typing import Any, Dict

from ecosystem.vqm.vqm_brain import VQMEcosystemBrain

# Simple singleton-ish brain instance
_brain: VQMEcosystemBrain | None = None


def get_brain() -> VQMEcosystemBrain:
    global _brain
    if _brain is None:
        _brain = VQMEcosystemBrain()
    return _brain


def run_vqm_cycle() -> Dict[str, Any]:
    """
    Perform a single ecosystem pulse and return the mesh state.
    """
    brain = get_brain()
    return brain.pulse()
