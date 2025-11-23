from __future__ import annotations

import time
from typing import Optional

from .models import (
    HookContext,
    AccountRoles,
    FeePolicy,
    PlannedTransfer,
    PlannedBundle,
)
from .fee_engine import compute_fee_drops
from .iso20022_bridge import build_pacs008_like, append_iso_record


def plan_payment_with_fee_and_iso(
    amount_drops: int,
    fee_policy: FeePolicy,
    accounts: AccountRoles,
    ctx: HookContext,
    *,
    end_to_end_suffix: Optional[str] = None,
    log_iso: bool = True,
) -> PlannedBundle:
    """
    Plan:

    - Main transfer: source -> vault (amount_drops)
    - Fee transfer:  source -> fee_pool (fee_drops)
    - ISO 20022-ish message describing the flow

    No network calls, no signing, no xrpl-py required here.
    This is a lab-side planner, not a live executor.
    """
    if amount_drops <= 0:
        raise ValueError("amount_drops must be positive")

    fee_drops = compute_fee_drops(amount_drops, fee_policy)

    main = PlannedTransfer(
        from_account=accounts.source,
        to_account=accounts.vault,
        amount_drops=amount_drops,
        purpose="main_payment",
    )

    fee_transfer: Optional[PlannedTransfer] = None
    if fee_drops > 0:
        fee_transfer = PlannedTransfer(
            from_account=accounts.source,
            to_account=accounts.fee_pool,
            amount_drops=fee_drops,
            purpose="protocol_fee",
        )

    # end_to_end_id for ISO record: time + ledger + optional suffix
    ts = int(time.time())
    suffix = end_to_end_suffix or "AETHER"
    end_to_end_id = f"{suffix}-{ctx.ledger_seq}-{ts}"

    iso_msg = build_pacs008_like(
        accounts=accounts,
        amount_drops=amount_drops,
        fee_drops=fee_drops,
        ctx=ctx,
        end_to_end_id=end_to_end_id,
    )

    if log_iso:
        append_iso_record(iso_msg)

    return PlannedBundle(
        main_transfer=main,
        fee_transfer=fee_transfer,
        iso20022_msg=iso_msg,
    )
