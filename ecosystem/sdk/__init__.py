"""
ecosystem.sdk
-------------
Integrator-friendly SDK for the Governor VQM stack.

This module exposes a high-level client that wraps:

  - Quantum Flow Engine v2
  - Transaction intents

It is:

  - READ-ONLY (no signing, no submission)
  - MAINNET-SAFE (RPC reads only)
"""

from .client import VQMSDKClient

__all__ = ["VQMSDKClient"]
