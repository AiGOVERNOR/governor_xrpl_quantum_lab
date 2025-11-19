"""
VQM Council

A multi-agent "governance brain" that turns raw network state +
predictive horizons into:

- mesh_intent (how the ecosystem should behave)
- scheduler plans (how jobs should be scaled)
- a council ledger of agent opinions

All of this is strictly off-chain and advisory.
"""

from .engine import build_council_decision

__all__ = [
    "build_council_decision",
]
