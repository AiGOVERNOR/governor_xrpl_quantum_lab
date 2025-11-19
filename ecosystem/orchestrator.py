from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict

from xrpl_rpc import XRPL_RPC
from ecosystem.guardian import XRPLGuardian


@dataclass
class NetworkState:
    ledger_seq: int
    txn_base_fee: int
    txn_median_fee: int
    recommended_fee_drops: int
    load_factor: float


def _read_network_state(rpc: XRPL_RPC) -> NetworkState:
    """
    Thin adapter from XRPL_RPC.get_fee_snapshot() into a structured dataclass.
    We assume XRPL_RPC is read-only and never holds secrets.
    """

    snap: Dict[str, Any] = rpc.get_fee_snapshot()

    return NetworkState(
        ledger_seq=int(snap.get("ledger_seq", 0)),
        txn_base_fee=int(snap.get("txn_base_fee", 10)),
        txn_median_fee=int(snap.get("txn_median_fee", 10)),
        recommended_fee_drops=int(snap.get("recommended_fee_drops", 10)),
        load_factor=float(snap.get("load_factor", 1.0)),
    )


def run_vqm_cycle() -> Dict[str, Any]:
    """
    One full VQM cycle:

      1. Read live XRPL fee / load snapshot (read-only)
      2. Classify network mode via XRPLGuardian
      3. Produce guardian view + network_state + metadata

    This function is safe to call in cron, uvicorn endpoints,
    or your autopush loop. It does NOT submit any transactions.
    """

    rpc = XRPL_RPC()
    net_state = _read_network_state(rpc)

    guardian = XRPLGuardian()
    guardian_view = guardian.guard(asdict(net_state))

    return {
        "pipeline_version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "network_state": asdict(net_state),
        "guardian": guardian_view,
    }
