"""
High-level operational context builder for the VQM ecosystem.

The context engine fuses:
- NeuroMesh scores
- meta-advisors
- network_state
into a single "context" object suitable for dashboards and decision engines.
"""

from .context import build_context

__all__ = ["build_context"]
