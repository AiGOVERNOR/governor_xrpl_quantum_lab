"""
Synthetic meta-advisors for the VQM ecosystem.

These do NOT talk to XRPL directly.
They only interpret the NeuroMesh + base state and
produce human-readable and machine-usable guidance.
"""

from .fee_meta import advise_fee_strategy
from .network_meta import advise_network_posture

__all__ = ["advise_fee_strategy", "advise_network_posture"]
