from dataclasses import dataclass
from typing import Any, Dict

from agents.vqm_xrpl_agent import VQM_XRPL_Agent, VQM_XRPL_Agent_Config


@dataclass
class NetworkSnapshot:
    ledger_seq: int
    load_factor: float
    txn_base_fee: int
    txn_median_fee: int
    recommended_fee_drops: int
    raw: Dict[str, Any]


class MainnetWatcher:
    """
    Thin wrapper around VQM_XRPL_Agent to keep a canonical
    "what does XRPL look like right now?" snapshot.

    This is LIVE mainnet telemetry only:
    - no signing
    - no trading
    - no wallet access
    """

    def __init__(self) -> None:
        self._agent = VQM_XRPL_Agent(VQM_XRPL_Agent_Config())

    def fetch_snapshot(self) -> NetworkSnapshot:
        raw = self._agent.get_network_snapshot()

        return NetworkSnapshot(
            ledger_seq=int(raw.get("ledger_seq", 0)),
            load_factor=float(raw.get("load_factor", 1.0)),
            txn_base_fee=int(raw.get("txn_base_fee", 10)),
            txn_median_fee=int(raw.get("txn_median_fee", 10)),
            recommended_fee_drops=int(
                raw.get("recommended_fee_drops", raw.get("txn_median_fee", 10))
            ),
            raw=raw,
        )

    def as_dict(self) -> Dict[str, Any]:
        snap = self.fetch_snapshot()
        return {
            "ledger_seq": snap.ledger_seq,
            "load_factor": snap.load_factor,
            "txn_base_fee": snap.txn_base_fee,
            "txn_median_fee": snap.txn_median_fee,
            "recommended_fee_drops": snap.recommended_fee_drops,
            "raw": snap.raw,
        }
