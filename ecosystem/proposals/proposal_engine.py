from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from ecosystem.telemetry.mainnet_watcher import NetworkSnapshot
from ecosystem.tools.tool_registry import ToolRegistry


@dataclass
class Proposal:
    id: str
    kind: str
    category: str
    created_at: str
    risk_level: int
    payload: Dict[str, Any]
    network_context: Dict[str, Any]


class ProposalEngine:
    """
    Generates mainnet-aware proposals for:
    - fee optimisation policies
    - payment/settlement rails
    - escrow milestone layouts
    - remittance routing

    It does NOT hold keys, sign, or broadcast.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _base_fields(self, kind: str, category: str, network: NetworkSnapshot) -> Dict[str, Any]:
        return {
            "id": str(uuid4()),
            "kind": kind,
            "category": category,
            "created_at": self._ts(),
            "risk_level": 2,  # default, relatively conservative
            "network_context": {
                "ledger_seq": network.ledger_seq,
                "load_factor": network.load_factor,
                "txn_base_fee": network.txn_base_fee,
                "txn_median_fee": network.txn_median_fee,
                "recommended_fee_drops": network.recommended_fee_drops,
            },
        }

    def propose_fee_policy(self, network: NetworkSnapshot) -> Proposal:
        base = self._base_fields("fee_policy", "fee", network)
        payload: Dict[str, Any] = {
            "description": "Recommended dynamic fee band for retail payments.",
            "min_drops": max(1, network.txn_base_fee),
            "target_drops": network.recommended_fee_drops,
            "max_drops": max(network.recommended_fee_drops * 3, 50),
            "strategy": "keep retail flows affordable while respecting open-ledger fee pressure",
        }
        return Proposal(
            payload=payload,
            **base,
        )

    def propose_streamed_payments(self, network: NetworkSnapshot) -> Proposal:
        base = self._base_fields("streamed_salary_protocol", "payment_protocol", network)
        payload = {
            "description": "XRPL StreamPay: salary / subscription payouts via periodic payments + escrows.",
            "interval_seconds": 3600,
            "recommended_fee_drops": network.recommended_fee_drops,
            "notes": "Design for US-style payroll overlays without trading.",
        }
        return Proposal(
            payload=payload,
            **base,
        )

    def propose_escrow_milestones(self, network: NetworkSnapshot) -> Proposal:
        base = self._base_fields("escrow_milestone_protocol", "escrow", network)
        payload = {
            "description": "Milestone-based escrows for projects/shipping flows.",
            "max_milestones": 10,
            "default_timeout_days": 30,
            "recommended_fee_drops": network.recommended_fee_drops,
        }
        return Proposal(
            payload=payload,
            **base,
        )

    def generate_all(self, network: NetworkSnapshot) -> List[Dict[str, Any]]:
        """
        Return a list of plain dict proposals for easy JSON exposure.
        """
        proposals = [
            self.propose_fee_policy(network),
            self.propose_streamed_payments(network),
            self.propose_escrow_milestones(network),
        ]

        tools_meta = [t.name for t in self.registry.list_tools()]
        out: List[Dict[str, Any]] = []
        for p in proposals:
            d = {
                "id": p.id,
                "kind": p.kind,
                "category": p.category,
                "created_at": p.created_at,
                "risk_level": p.risk_level,
                "payload": p.payload,
                "network_context": p.network_context,
                "tools_consulted": tools_meta,
                "execution_mode": "proposal_only",
                "requires_signing": False,
            }
            out.append(d)
        return out
