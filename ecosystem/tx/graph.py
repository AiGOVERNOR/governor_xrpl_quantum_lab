"""
Protocol graph + selector (self-healing)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class ProtocolSelector:
    """
    Modern selector API:

        select_for_intent(
            intent: Dict[str, Any],
            band: str,
            guardian_mode: str,
            risk_budget: int
        )

    Previous versions accepted fewer arguments.
    This selector is *self-healing* and tolerates missing inputs.
    """

    def __init__(self) -> None:
        self.version = "2.0.0"

    def _protocols(self) -> List[str]:
        return [
            "simple_payment_v1",
            "simple_payment_v2",
            "escrow_milestone_v1",
        ]

    def select_for_intent(
        self,
        intent: Dict[str, Any],
        band: Optional[str] = None,
        guardian_mode: Optional[str] = None,
        risk_budget: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Self-healing selector:
          - Accepts missing band/guardian_mode/risk_budget
          - Applies fallback defaults
          - Always returns a protocol + reason + score + risk
        """

        band = band or "normal"
        guardian_mode = guardian_mode or "unknown"
        risk_budget = risk_budget if isinstance(risk_budget, int) else 3

        intent_kind = intent.get("kind", "unknown")

        # crude risk model
        base_risk = {
            "simple_payment": 2,
            "escrow": 4,
            "unknown": 3,
        }.get(intent_kind, 3)

        # network pressure multiplication
        band_penalty = {
            "low": 0,
            "normal": 1,
            "elevated": 2,
            "extreme": 3,
        }.get(band, 1)

        final_risk = min(10, base_risk + band_penalty)

        # pick simplest workable protocol
        if intent_kind == "simple_payment":
            protocol = "simple_payment_v2"
        elif intent_kind == "escrow":
            protocol = "escrow_milestone_v1"
        else:
            protocol = "simple_payment_v1"

        score = max(0.1, 1.0 - (final_risk / 10.0))

        return {
            "protocol": protocol,
            "reason": f"intent={intent_kind}; band={band}; guardian_mode={guardian_mode}; risk={final_risk}",
            "risk_level": final_risk,
            "score": round(score, 3),
            "version": self.version,
        }
