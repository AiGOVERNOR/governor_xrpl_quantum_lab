"""
Neural coordination layer for the VQM ecosystem.

This package exposes high-level functions that fuse:
- network_state
- guardian outputs
- fee horizon
- scheduler decisions
- tool scores

into a single "NeuroMesh" state object.
"""

from .neuro_mesh import build_neuromesh_state

__all__ = ["build_neuromesh_state"]
