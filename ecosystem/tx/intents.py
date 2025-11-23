"""
ecosystem.tx.intents
--------------------
Transaction Intents for Governor XRPL Quantum Lab.

These describe WHAT we want to do — not how.
The Brain + Router decide protocols and safety.
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TxIntent:
    kind: str
    amount_drops: int
    source_account: str
    destination_account: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Backwards-compatible helper (used by existing CLIs)
    @staticmethod
    def new(
        kind: str,
        amount_drops: int,
        source_account: str,
        destination_account: str,
        metadata: Dict[str, Any],
    ) -> "TxIntent":
        return TxIntent(
            kind=kind,
            amount_drops=amount_drops,
            source_account=source_account,
            destination_account=destination_account,
            metadata=metadata or {},
        )

    # Convenience constructors for Phase-E protocols
    @staticmethod
    def simple_payment(
        amount_drops: int,
        source_account: str,
        destination_account: str,
        note: str = "",
    ) -> "TxIntent":
        return TxIntent(
            kind="simple_payment",
            amount_drops=amount_drops,
            source_account=source_account,
            destination_account=destination_account,
            metadata={"note": note} if note else {},
        )

    @staticmethod
    def escrow_milestone(
        amount_drops: int,
        source_account: str,
        destination_account: str,
        milestones: int = 3,
        timeout_days: int = 30,
        note: str = "",
    ) -> "TxIntent":
        meta: Dict[str, Any] = {
            "milestones": milestones,
            "timeout_days": timeout_days,
        }
        if note:
            meta["note"] = note
        return TxIntent(
            kind="escrow_milestone",
            amount_drops=amount_drops,
            source_account=source_account,
            destination_account=destination_account,
            metadata=meta,
        )

    @staticmethod
    def streamed_salary(
        amount_drops: int,
        source_account: str,
        destination_account: str,
        interval_seconds: int = 3600,
        note: str = "",
    ) -> "TxIntent":
        meta: Dict[str, Any] = {
            "interval_seconds": interval_seconds,
        }
        if note:
            meta["note"] = note
        return TxIntent(
            kind="streamed_salary",
            amount_drops=amount_drops,
            source_account=source_account,
            destination_account=destination_account,
            metadata=meta,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "amount_drops": self.amount_drops,
            "source_account": self.source_account,
            "destination_account": self.destination_account,
            "metadata": self.metadata,
        }
