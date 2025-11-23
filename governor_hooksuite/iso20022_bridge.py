from __future__ import annotations

import json
import os
from typing import Dict, Any

from .models import HookContext, AccountRoles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
OUTBOX_PATH = os.path.join(CONFIG_DIR, "iso20022_outbox.jsonl")


def _ensure_outbox() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    # File is created lazily when first appended.


def build_pacs008_like(
    accounts: AccountRoles,
    amount_drops: int,
    fee_drops: int,
    ctx: HookContext,
    end_to_end_id: str,
) -> Dict[str, Any]:
    """
    Build an ISO 20022-ish pacs.008-like JSON structure describing:

    - debtor: source account
    - creditor: vault account
    - fee leg: fee_pool account
    """
    value_xrp = amount_drops / 1_000_000
    fee_xrp = fee_drops / 1_000_000

    return {
        "msg_type": "pacs.008-like",
        "schema": "AETHERBORN-ISO20022-v1",
        "debtor": {
            "name": "Governor AETHERBORN Source",
            "id": accounts.source,
            "rail_hint": "XRPL",
        },
        "creditor": {
            "name": "Governor AETHERBORN Vault",
            "id": accounts.vault,
            "rail_hint": "XRPL",
        },
        "fee_beneficiary": {
            "name": "Governor Infra Fee Pool",
            "id": accounts.fee_pool,
            "rail_hint": "XRPL",
        },
        "intermediary_chain": ctx.network_name,
        "amount": {
            "currency": "XRP",
            "value": f"{value_xrp:.6f}",
            "value_drops": amount_drops,
        },
        "charges": {
            "estimated_network_fee_drops": ctx.base_fee_drops,
            "protocol_fee_drops": fee_drops,
            "protocol_fee_value": f"{fee_xrp:.6f}",
        },
        "context": {
            "ledger_seq": ctx.ledger_seq,
            "load_factor": ctx.load_factor,
            "median_fee_drops": ctx.median_fee_drops,
            "base_fee_drops": ctx.base_fee_drops,
            "network_name": ctx.network_name,
        },
        "end_to_end_id": end_to_end_id,
        "purpose": "XRPL internal profit routing; exportable for legacy rails reporting",
    }


def append_iso_record(record: Dict[str, Any], outbox_path: str = OUTBOX_PATH) -> None:
    """
    Append one JSON record to iso20022_outbox.jsonl (JSON per line).
    """
    _ensure_outbox()
    line = json.dumps(record, separators=(",", ":"))
    with open(outbox_path, "a") as f:
        f.write(line + "\n")
