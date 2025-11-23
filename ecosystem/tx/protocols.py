# ecosystem/tx/protocols.py
# Fully rewritten, complete, aligned with TxBrain, Multileg, RouterV3, FlowEngine

from __future__ import annotations
from typing import Any, Dict, Optional, List
from ecosystem.tx.intents import TxIntent

###############################################################################
# SIMPLE PAYMENT V1 — BASELINE FIXED-FEE XRPL PAYMENT
###############################################################################

def simple_payment_v1(
    intent: TxIntent,
    network_state: Dict[str, Any],
    guardian_hint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Basic XRPL payment with static fee.
    """
    median = int(network_state.get("txn_median_fee", 10))
    recommended = int(network_state.get("recommended_fee_drops", median))
    safe_fee = recommended  # v1 does NOT use safety buffer

    return {
        "intent_kind": intent.kind,
        "network_state": {
            **network_state,
            "safe_fee_drops": safe_fee
        },
        "protocol": "simple_payment_v1",
        "risk": {
            "level": 1,
            "reasons": ["static_fee", "baseline_protocol"]
        },
        "steps": [
            {
                "name": "check_accounts",
                "details": {
                    "source": intent.source_account,
                    "destination": intent.destination_account
                }
            },
            {
                "name": "prepare_payment_instruction",
                "details": {
                    "amount_drops": intent.amount_drops,
                    "fee_drops": safe_fee
                }
            }
        ]
    }

###############################################################################
# SIMPLE PAYMENT V2 — DYNAMIC FEE + SAFETY BUFFER
###############################################################################

def simple_payment_v2(
    intent: TxIntent,
    network_state: Dict[str, Any],
    guardian_hint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dynamic fee selection with safety buffer.
    """
    median = int(network_state.get("txn_median_fee", 10))
    recommended = int(network_state.get("recommended_fee_drops", median))
    safe_fee = int(recommended * 1.1)

    return {
        "intent_kind": intent.kind,
        "network_state": {
            **network_state,
            "safe_fee_drops": safe_fee
        },
        "protocol": "simple_payment_v2",
        "risk": {
            "level": 2,
            "reasons": [
                "dynamic_fee",
                "safety_buffer",
                "median_fee_based"
            ]
        },
        "steps": [
            {
                "name": "check_accounts",
                "details": {
                    "source": intent.source_account,
                    "destination": intent.destination_account
                }
            },
            {
                "name": "estimate_fee_with_buffer",
                "details": {
                    "median_fee": median,
                    "recommended_fee": recommended,
                    "safe_fee": safe_fee
                }
            },
            {
                "name": "prepare_payment_instruction",
                "details": {
                    "amount_drops": intent.amount_drops
                }
            }
        ]
    }

###############################################################################
# ESCROW MILESTONE V1 — MULTI-MILESTONE DELIVERY ESCROW
###############################################################################

def escrow_milestone_v1(
    intent: TxIntent,
    network_state: Dict[str, Any],
    guardian_hint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Handles project/shipping milestone-style XRPL escrows.
    """
    meta = intent.metadata or {}

    raw = meta.get("milestones", 3)

    if isinstance(raw, int):
        milestones = raw
    elif isinstance(raw, list):
        milestones = len(raw)
    else:
        raise TypeError("milestones must be int or list")

    return {
        "intent_kind": intent.kind,
        "network_state": network_state,
        "protocol": "escrow_milestone_v1",
        "milestones": milestones,
        "risk": {
            "level": 3,
            "reasons": ["escrow_protocol", "multi-stage_release"]
        },
        "steps": [
            {
                "name": "prepare_escrow_setup",
                "details": {
                    "milestone_count": milestones
                }
            }
        ]
    }
