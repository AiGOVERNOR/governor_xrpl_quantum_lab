"""
ecosystem.tx
------------
Quantum AI Transaction Protocol Brain for Governor XRPL Quantum Lab.

This package is **read-only and non-signing**:
- It designs transaction *blueprints* (Python dicts / JSON-ready).
- It NEVER signs, NEVER submits, NEVER trades.

Flow:
    intent -> protocol selection -> XRPL tx blueprints (+ safety notes)
"""

from .intents import TxIntent
from .brain import tx_brain

__all__ = ["TxIntent", "tx_brain"]
