"""
ecosystem.router_v3
-------------------
Quantum Router Layer V3 — protocol selection + safety scoring.

Advisory-only, read-only.
No signing. No transaction submission.
"""

from typing import Dict, Any, Tuple


def _guardian_mode(guardian: Dict[str, Any] | None) -> str:
    if not guardian:
        return "unknown"
    return (
        guardian.get("mesh", {}).get("mode")
        or guardian.get("policy", {}).get("mode")
        or guardian.get("mode")
        or "unknown"
    )


class TransactionRouterV3:
    """
    Scores protocol plans against live network conditions + guardian mode.
    """

    @staticmethod
    def _band_from_fee(median_fee: int) -> str:
        if median_fee <= 20:
            return "low"
        if median_fee <= 200:
            return "normal"
        if median_fee <= 2000:
            return "elevated"
        return "extreme"

    @staticmethod
    def _apply_risk_envelope(
        base_risk: int, band: str, guardian_mode: str
    ) -> Tuple[int, float]:
        """
        Take a base risk (1-5), adjust for band + guardian_mode,
        and return (final_risk, score 0-1).
        """
        risk = base_risk

        if band in ("elevated", "extreme"):
            risk += 1
        if guardian_mode == "fee_pressure":
            risk += 1

        risk = max(1, min(risk, 5))

        # Higher risk -> lower score. 1 => 1.0, 5 => 0.4
        score = 1.0 - 0.15 * (risk - 1)
        if score < 0.1:
            score = 0.1

        return risk, score

    def route(
        self,
        intent,
        protocol_plan: Dict[str, Any],
        network_state: Dict[str, Any],
        guardian: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        median = network_state["txn_median_fee"]
        load = network_state["load_factor"]
        band = self._band_from_fee(median)
        guardian_mode = _guardian_mode(guardian)

        base_risk = protocol_plan.get("risk", {}).get("level", 2)
        final_risk, score = self._apply_risk_envelope(
            base_risk=base_risk, band=band, guardian_mode=guardian_mode
        )

        candidate = {
            "protocol": protocol_plan["protocol"],
            "score": round(score, 3),
            "reason": (
                f"intent={intent.kind}; band={band}; "
                f"guardian_mode={guardian_mode}; risk={final_risk}"
            ),
            "risk": {
                "base_level": base_risk,
                "final_level": final_risk,
            },
        }

        return {
            "selected": candidate,
            "candidates": [candidate],
            "meta": {
                "median_fee": median,
                "recommended_fee": network_state["recommended_fee_drops"],
                "load_factor": load,
                "band": band,
                "guardian_mode": guardian_mode,
                "notes": [
                    "Router V3 is advisory-only.",
                    "Uses protocol_plan.risk + live XRPL conditions.",
                ],
            },
        }


router_v3 = TransactionRouterV3()
