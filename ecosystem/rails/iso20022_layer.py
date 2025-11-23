"""
ecosystem/rails/iso20022_layer.py

AETHERBORN Multi-Rail / ISO 20022 Layer

This module turns XRPL actions into ISO 20022-style payment messages
and stores them in a JSONL outbox for downstream rails (banks, cores,
other chains, batch pipelines, etc.).

Key responsibilities:
- Build "pacs.008-like" envelopes for XRPL payments.
- Persist outbound messages into config/iso20022_outbox.jsonl.
- Provide a simple, typed "PlannedTransfer" structure compatible
  with both AETHERBORN SWARM and any future routers.
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Default outbox location (aligned with your current lab)
ISO20022_OUTBOX_PATH = "config/iso20022_outbox.jsonl"


@dataclass
class PlannedTransfer:
    """
    A generic planned transfer, rail-agnostic but XRPL-friendly.

    amount_drops: integer amount in XRP drops.
    currency:     logical currency code (XRP, USD, etc.)
    rail:         source rail (e.g. XRPL, HOOKS, XAHAU, BANK_CORE)
    purpose:      free-text purpose flag (main_payment, profit_routing, fee, etc.)
    end_to_end_id: optional externally supplied unique identifier.
    """
    from_account: str
    to_account: str
    amount_drops: int
    currency: str = "XRP"
    rail: str = "XRPL"
    purpose: str = "internal"
    end_to_end_id: Optional[str] = None


def _utc_iso() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _ensure_parent_dir(path: str) -> None:
    """Ensure the directory for a given file exists."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def append_iso_record(record: Dict[str, Any],
                      outbox_path: str = ISO20022_OUTBOX_PATH) -> None:
    """
    Append a single ISO-style JSON record to the outbox as one line of JSON.

    This is intentionally simple and append-only so other processes can
    tail / batch / ETL this file easily.
    """
    _ensure_parent_dir(outbox_path)
    with open(outbox_path, "a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def build_pacs008_like(
    transfer: PlannedTransfer,
    *,
    ledger_seq: Optional[int] = None,
    network_name: str = "XRPL-MAINNET",
    profile: str = "AETHERBORN-ISO20022-v1",
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a "pacs.008-like" ISO 20022 payment message as JSON.

    This is not a strict XML ISO 20022 message; it's a JSON-mapped,
    field-compatible envelope that back-office / ETL / bank-core layers
    can normalize into their own schemas.
    """
    if transfer.amount_drops < 0:
        raise ValueError("amount_drops must be non-negative")

    # Derive XRP value from drops (6 decimal places)
    value_xrp = transfer.amount_drops / 1_000_000
    end_to_end_id = (
        transfer.end_to_end_id
        or f"AETHER-{uuid.uuid4().hex[:16]}-{int(datetime.now(timezone.utc).timestamp())}"
    )

    base_context: Dict[str, Any] = {
        "profile": profile,
        "network": network_name,
        "created_at": _utc_iso(),
    }
    if ledger_seq is not None:
        base_context["ledger_seq"] = ledger_seq

    if context:
        # Caller-supplied fields override base context where keys match
        base_context.update(context)

    message = {
        "msg_type": "pacs.008-like",
        "schema": profile,
        "end_to_end_id": end_to_end_id,
        "creation_timestamp": _utc_iso(),
        "rail": transfer.rail,
        "debtor": {
            "name": "Governor AETHERBORN Source",
            "id": transfer.from_account,
            "rail_hint": transfer.rail,
        },
        "creditor": {
            "name": "Governor AETHERBORN Destination",
            "id": transfer.to_account,
            "rail_hint": transfer.rail,
        },
        "intermediary_chain": transfer.rail,
        "amount": {
            "currency": transfer.currency,
            "value": f"{value_xrp:.6f}",
            "value_drops": transfer.amount_drops,
        },
        "charges": {
            # You can extend this with structured network fee modeling later
            "estimated_network_fee_drops": None,
        },
        "purpose": transfer.purpose,
        "context": base_context,
    }

    return message


def record_xrpl_internal_payment(
    *,
    from_account: str,
    to_account: str,
    amount_drops: int,
    purpose: str,
    ledger_seq: Optional[int],
    median_fee_drops: Optional[int],
    safe_fee_drops: Optional[int],
    outbox_path: str = ISO20022_OUTBOX_PATH,
) -> str:
    """
    High-level helper used by AETHERBORN SWARM:

    - Wraps a XRPL internal payment as an ISO-style JSON message.
    - Persists it to iso20022_outbox.jsonl
    - Returns the end_to_end_id for correlation with on-ledger txns.
    """
    transfer = PlannedTransfer(
        from_account=from_account,
        to_account=to_account,
        amount_drops=amount_drops,
        currency="XRP",
        rail="XRPL",
        purpose=purpose,
    )

    context = {
        "median_fee_drops": median_fee_drops,
        "safe_fee_drops": safe_fee_drops,
    }

    msg = build_pacs008_like(
        transfer,
        ledger_seq=ledger_seq,
        network_name="XRPL-MAINNET",
        profile="AETHERBORN-ISO20022-v1",
        context=context,
    )

    append_iso_record(msg, outbox_path=outbox_path)
    return msg["end_to_end_id"]


def load_outbox(
    outbox_path: str = ISO20022_OUTBOX_PATH,
) -> list[Dict[str, Any]]:
    """
    Utility for debugging / dashboards:
    Load all ISO outbox records as a list of dicts.
    """
    if not os.path.exists(outbox_path):
        return []

    records = []
    with open(outbox_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # Keep the lab resilient – skip corrupt lines, but don't crash.
                continue
    return records


if __name__ == "__main__":
    # Simple self-test harness so you can run:
    #   python -m ecosystem.rails.iso20022_layer
    demo_transfer = PlannedTransfer(
        from_account="rEXdG3Rh9Ejb3NKXoxb16xge4d3BHskJUP",
        to_account="rK7BKKcayjcbwAdYBj1XnAy1hR2zesTqQZ",
        amount_drops=123456,
        purpose="lab_demo",
    )

    msg = build_pacs008_like(
        demo_transfer,
        ledger_seq=100_000_000,
        context={"demo": True},
    )
    append_iso_record(msg)
    print("Wrote demo ISO 20022-style record to", ISO20022_OUTBOX_PATH)
    print("end_to_end_id:", msg["end_to_end_id"])
