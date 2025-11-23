from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class FeePolicy:
    """
    Fee policy for protocol-level routing / infra.

    - bps:           basis points (1 bps = 0.01%). 5 bps = 0.05%.
    - min_drops:     minimum fee in drops (to avoid microscopic dust).
    - max_bps:       safety cap so we never accidentally charge 5000 bps.
    """

    bps: int = 5
    min_drops: int = 10
    max_bps: int = 50

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeePolicy":
        return cls(
            bps=int(data.get("bps", 5)),
            min_drops=int(data.get("min_drops", 10)),
            max_bps=int(data.get("max_bps", 50)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bps": self.bps,
            "min_drops": self.min_drops,
            "max_bps": self.max_bps,
        }


@dataclass
class AccountRoles:
    """
    Logical roles in the lab infra.

    - source:        trading / working capital account (e.g., your Aetherborn wallet)
    - vault:         long-term / profit vault
    - fee_pool:      where infra / routing fees go (can be same as vault)
    - treasury:      optional separate treasury
    """

    source: str
    vault: str
    fee_pool: str
    treasury: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountRoles":
        return cls(
            source=data["source"],
            vault=data["vault"],
            fee_pool=data.get("fee_pool", data["vault"]),
            treasury=data.get("treasury"),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "source": self.source,
            "vault": self.vault,
            "fee_pool": self.fee_pool,
        }
        if self.treasury:
            result["treasury"] = self.treasury
        return result


@dataclass
class HookContext:
    """
    Context snapshot used when planning a "hook-like" bundle.

    This is the info a real hook / smart contract would see on-ledger.
    Here, we model it in Python so agents can simulate / test flows.
    """

    ledger_seq: int
    load_factor: float
    median_fee_drops: int
    base_fee_drops: int
    network_name: str = "XRPL-mainnet"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ledger_seq": self.ledger_seq,
            "load_factor": self.load_factor,
            "median_fee_drops": self.median_fee_drops,
            "base_fee_drops": self.base_fee_drops,
            "network_name": self.network_name,
        }


@dataclass
class PlannedTransfer:
    """
    A planned transfer intent. This is not an actual signed transaction,
    just the logical "what" that an agent can translate into xrpl-py Payment.

    amount_drops: integer XRP amount (in drops)
    """

    from_account: str
    to_account: str
    amount_drops: int
    purpose: str  # e.g. "main_payment", "fee", "rebalance"


@dataclass
class PlannedBundle:
    """
    Represents a "hook-like" bundle:

    - main_transfer: the primary trade leg
    - fee_transfer:  optional protocol fee leg
    - iso20022_msg:  ISO-style representation of the flow
    """

    main_transfer: PlannedTransfer
    fee_transfer: Optional[PlannedTransfer]
    iso20022_msg: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "main_transfer": self.main_transfer.__dict__,
            "fee_transfer": self.fee_transfer.__dict__ if self.fee_transfer else None,
            "iso20022_msg": self.iso20022_msg,
        }
