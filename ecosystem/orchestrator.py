"""
VQM Orchestrator – Level 3

One cycle does:
  1. Read XRPL mainnet network_state from XRPL_RPC (read-only).
  2. Pass it to GuardianVQMPipeline (policy + fee mode).
  3. Return a structured snapshot for CLI / API / logging.

No transactions are signed.
No trading is performed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from xrpl_rpc import XRPL_RPC
from ecosystem.guardian import GuardianVQMPipeline, GuardianConfig


def _read_network_state(rpc: XRPL_RPC) -> Dict[str, Any]:
    """
    Normalize XRPL_RPC.get_fee_snapshot() into a small, stable dict.
    """
    snap: Dict[str, Any] = rpc.get_fee_snapshot()

    return {
        "ledger_seq": snap.get("ledger_seq"),
        "txn_base_fee": snap.get("txn_base_fee"),
        "txn_median_fee": snap.get("txn_median_fee"),
        "recommended_fee_drops": snap.get("recommended_fee_drops"),
        "load_factor": snap.get("load_factor", 1.0),
    }


def run_vqm_cycle() -> Dict[str, Any]:
    """
    Run a single VQM cycle:
      - snapshot XRPL fee state
      - assess it with Guardian
      - include AI fee reducer output (inside guardian dict)
    """
    rpc = XRPL_RPC()
    net_state = _read_network_state(rpc)

    guardian = GuardianVQMPipeline(GuardianConfig())
    guardian_state = guardian.assess(net_state)

    return {
        "network_state": net_state,
        "guardian": guardian_state,
        "pipeline_version": guardian.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
