"""
Governor HookSuite v1.0 (Lab-side, off-chain)

This package is the “contract layer” of the Governor XRPL Quantum Lab.
It does NOT deploy anything on-chain. Instead, it:

- Centralizes fee policy and infrastructure roles
- Builds ISO20022-style messages for legacy rails
- Plans "hook-like" flows: main payments + fee legs + logging
- Keeps everything XRPL/Xahau-ready without pretending to be live hooks

On-chain hooks / contracts (Xahau, etc.) would eventually mirror this logic,
but this code is safe to run as pure Python in Termux.
"""

from .models import (
    HookContext,
    FeePolicy,
    AccountRoles,
    PlannedTransfer,
    PlannedBundle,
)
from .config import load_hooks_config, DEFAULT_CONFIG_PATH
from .fee_engine import compute_fee_drops
from .iso20022_bridge import build_pacs008_like, append_iso_record
from .hook_planner import plan_payment_with_fee_and_iso

__all__ = [
    "HookContext",
    "FeePolicy",
    "AccountRoles",
    "PlannedTransfer",
    "PlannedBundle",
    "load_hooks_config",
    "DEFAULT_CONFIG_PATH",
    "compute_fee_drops",
    "build_pacs008_like",
    "append_iso_record",
    "plan_payment_with_fee_and_iso",
]
