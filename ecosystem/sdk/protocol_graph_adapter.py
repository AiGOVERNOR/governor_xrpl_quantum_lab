"""
ecosystem.sdk.protocol_graph_adapter
------------------------------------
Thin helper so external SDK callers can query the ProtocolGraph
in a clean, stable way.

This stays READ-ONLY and returns plain dicts.
"""


from __future__ import annotations

from typing import Any, Dict

from ecosystem.tx.graph import protocol_graph


def summarize_graph() -> Dict[str, Any]:
    """
    Return a compact snapshot of the protocol graph.
    Safe to expose via API or SDK.
    """
    return {
        "protocols": protocol_graph.list_protocols(),
        "transitions": protocol_graph.list_transitions(),
    }


def advise(
    intent_kind: str,
    band: str,
    guardian_mode: str,
    risk_budget: int = 3,
) -> Dict[str, Any]:
    """
    SDK-facing advisory helper.

    Example:
      advise(
        intent_kind="simple_payment",
        band="extreme",
        guardian_mode="fee_pressure",
        risk_budget=3,
      )
    """
    return protocol_graph.advise_for_intent(
        intent_kind=intent_kind,
        band=band,
        guardian_mode=guardian_mode,
        risk_budget=risk_budget,
    )
