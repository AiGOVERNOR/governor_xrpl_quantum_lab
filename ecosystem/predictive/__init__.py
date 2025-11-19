"""
Predictive Engine for VQM

Lightweight, stateless helpers that transform historical memory into
short/long-term fee and load trends. No ML frameworks, no on-chain
actions—purely advisory and read-only.
"""

from .engine import build_fee_horizon

__all__ = [
    "build_fee_horizon",
]
