"""
ecosystem.tx.router
-------------------
Transaction Brain V2 Router Layer.

This is a *read-only*, *no-trading* router that:
- Looks at the current XRPL network_state (fees, load_factor, etc.)
- Peeks at Guardian / Mesh hints (mode = normal / fee_pressure / etc.)
- Examines the TxIntent (kind, amount, metadata)
- Produces a routing decision object describing which protocol family
  should be used (e.g. simple_payment_v1) and why.

It does NOT:
- Construct or submit transactions
- Sign anything
- Talk to wallets
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from ecosystem.tx.intents import TxIntent


@dataclass
class TxRouteCandidate:
    """
    Represents one candidate protocol the router considered.
    """
    protocol: str
    score: float
    reason: str


@dataclass
class TxRouteDecision:
    """
    Final router output.

    selected: the chosen protocol
    candidates: list of all options considered
    meta: extra context (band, guardian_mode, notes)
    """
    selected: TxRouteCandidate
    candidates: List[TxRouteCandidate]
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected": asdict(self.selected),
            "candidates": [asdict(c) for c in self.candidates],
            "meta": self.meta,
        }


class TransactionRouterV2:
    """
    Quantum-ish transaction router.

    For now we keep the routing logic intentionally simple and conservative:
    - We always choose a safe protocol supported by the current brain
      (e.g. 'simple_payment_v1').
    - We *describe* future protocol families in metadata, without depending
      on them being implemented yet.
    """

    def route(
        self,
        intent: TxIntent,
        network_state: Dict[str, Any],
        guardian_hint: Optional[Dict[str, Any]] = None,
    ) -> TxRouteDecision:
        # Extract core network parameters
        median_fee = network_state.get("txn_median_fee", 10)
        recommended_fee = network_state.get("recommended_fee_drops", median_fee)
        load_factor = network_state.get("load_factor", 1.0)

        guardian_mode = None
        if guardian_hint:
            guardian_mode = (
                guardian_hint.get("mesh", {}) or {}
            ).get("mode") or guardian_hint.get("policy", {}).get("mode")

        # --- Simple banding model (local to router) ---
        if median_fee <= 20:
            band = "low"
        elif median_fee <= 200:
            band = "normal"
        elif median_fee <= 2000:
            band = "elevated"
        else:
            band = "extreme"

        candidates: List[TxRouteCandidate] = []

        # ------------------------------------------------------------------
        # Intent-aware routing
        # ------------------------------------------------------------------
        if intent.kind == "simple_payment":
            # Today: we only execute 'simple_payment_v1' in the brain.
            # Future: we might branch into 'streamed_payment_v1', etc.
            reason_bits = [f"intent=simple_payment", f"band={band}", f"guardian_mode={guardian_mode or 'unknown'}"]
            reason = "; ".join(reason_bits)

            candidates.append(
                TxRouteCandidate(
                    protocol="simple_payment_v1",
                    score=1.0,
                    reason=reason,
                )
            )
            selected = candidates[0]

        else:
            # Unknown intent kinds fall back to a generic safe protocol hint.
            reason_bits = [f"intent={intent.kind}", "fallback=generic_protocol"]
            reason = "; ".join(reason_bits)

            candidates.append(
                TxRouteCandidate(
                    protocol="generic_protocol_v1",
                    score=0.5,
                    reason=reason,
                )
            )
            selected = candidates[0]

        meta = {
            "band": band,
            "load_factor": load_factor,
            "median_fee": median_fee,
            "recommended_fee": recommended_fee,
            "guardian_mode": guardian_mode,
            "notes": [
                "Router is advisory-only. It does not submit or sign.",
                "Execution is still handled by TransactionProtocolBrain.",
            ],
        }

        return TxRouteDecision(
            selected=selected,
            candidates=candidates,
            meta=meta,
        )
