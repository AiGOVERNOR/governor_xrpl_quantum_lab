# ecosystem/protocol_graph.py
"""
protocol_graph.py — minimal guaranteed-importable protocol selector.

This file is intentionally simple and robust to ensure:
- Import always succeeds
- Tools can call select_for_intent() with extra kwargs
- Protocol graphs exist even if nothing else is present
"""

from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# Public exports
# ------------------------------------------------------------
__all__ = [
    "build_default_graph",
    "ProtocolSelector",
]


# ------------------------------------------------------------
# Build a simple protocol graph
# ------------------------------------------------------------
def build_default_graph() -> List[Dict[str, Any]]:
    return [
        {
            "name": "simple_payment_v1",
            "kind": "payment",
            "risk_level": 1,
        },
        {
            "name": "simple_payment_v2",
            "kind": "payment",
            "risk_level": 2,
        },
        {
            "name": "stream_pay_v1",
            "kind": "stream",
            "risk_level": 3,
        },
        {
            "name": "escrow_milestone_v1",
            "kind": "escrow",
            "risk_level": 3,
        },
    ]


# ------------------------------------------------------------
# ProtocolSelector class
# ------------------------------------------------------------
class ProtocolSelector:
    VERSION = "2.0.0"

    def __init__(self, graph: Optional[List[Dict[str, Any]]] = None) -> None:
        self._graph = graph or build_default_graph()

    # --------------------------------------------------------
    def select_for_intent(
        self,
        intent_kind: str,
        band: str = "normal",
        guardian_mode: str = "unknown",
        risk_budget: int = 3,
        **_extra: Any,
    ) -> Dict[str, Any]:
        """
        Select a protocol for an intent.

        Accepts arbitrary extra kwargs (ignored),
        so older AND newer callers both work.
        """

        # Map flows → candidate protocols
        if intent_kind in ("simple_payment", "payment"):
            candidates = [
                self._get("simple_payment_v1"),
                self._get("simple_payment_v2"),
            ]
        elif intent_kind in ("stream", "salary_stream"):
            candidates = [self._get("stream_pay_v1")]
        elif intent_kind in ("escrow", "escrow_milestone"):
            candidates = [self._get("escrow_milestone_v1")]
        else:
            candidates = [self._get("simple_payment_v1")]

        # Honor risk_budget
        filtered = [p for p in candidates if p["risk_level"] <= risk_budget]
        if not filtered:
            filtered = candidates

        # Always pick lowest-risk valid protocol
        filtered.sort(key=lambda p: p["risk_level"])
        selected = filtered[0]

        score = 1.0 / (selected["risk_level"] + 1)

        return {
            "protocol": selected["name"],
            "risk_level": selected["risk_level"],
            "reason": f"risk={selected['risk_level']}, band={band}, guardian={guardian_mode}",
            "score": score,
            "version": self.VERSION,
        }

    # --------------------------------------------------------
    def _get(self, name: str) -> Dict[str, Any]:
        for p in self._graph:
            if p["name"] == name:
                return p
        raise KeyError(f"Protocol not found: {name}")
