# ecosystem/tx/router_v3.py
"""
router_v3.py — Governor Quantum Router v3.4 (Mueller Fix Edition)

Goals:
  - Accept BOTH old and new call styles:
        route(intent, guardian_hint=...)
        route(intent, network_state, quantum, tx_plan)
        route(intent=intent, network_state=..., quantum=..., tx_plan=...)

  - Accept both TxIntent objects and plain dicts.

Router is advisory-only: it never submits or signs transactions.
"""

from typing import Any, Dict, Union, Optional

from ecosystem.tx.intents import TxIntent


IntentLike = Union[TxIntent, Dict[str, Any]]


class TxRouterV3:
    VERSION = "3.4.0"

    # ------------------------------------------------------------
    def _intent_kind(self, intent: IntentLike) -> str:
        """Normalize intent.kind from TxIntent or dict."""
        if isinstance(intent, TxIntent):
            return intent.kind
        if isinstance(intent, dict):
            return intent.get("kind", "unknown")
        return "unknown"

    # ------------------------------------------------------------
    def route(
        self,
        intent: IntentLike,
        network_state: Optional[Dict[str, Any]] = None,
        quantum: Optional[Dict[str, Any]] = None,
        tx_plan: Optional[Dict[str, Any]] = None,
        guardian_hint: Optional[Dict[str, Any]] = None,
        **_ignore: Any,
    ) -> Dict[str, Any]:
        """
        Decide which protocol to use for this intent.

        Parameters:
          intent: TxIntent or dict with at least "kind"
          network_state: normalized network_state dict (currently unused for scoring)
          quantum: quantum signal dict (preferred parameter name going forward)
          guardian_hint: legacy alias for quantum
          tx_plan: transaction plan from the transaction brain (unused, but accepted)

        Returns a dict:
          {
            "protocol": "simple_payment_v2",
            "reason": "...",
            "risk": {...},
            "score": float,
            "version": "3.4.0",
          }
        """
        # Prefer explicit quantum; fall back to guardian_hint; default empty
        qsig: Dict[str, Any] = (quantum or guardian_hint or {})  # type: ignore[assignment]

        kind = self._intent_kind(intent)
        band = qsig.get("band", "normal")
        guardian_mode = qsig.get("guardian_mode", "unknown")

        # Base risk according to protocol design
        base_risk = 2

        # Adjust risk according to network band
        if band in ("elevated", "extreme"):
            base_risk += 2

        final_risk = base_risk

        return {
            "protocol": "simple_payment_v2",
            "reason": (
                f"intent={kind}; band={band}; guardian={guardian_mode}; "
                f"risk={final_risk}"
            ),
            "risk": {
                "base_level": base_risk,
                "final_level": final_risk,
            },
            "score": 0.4,
            "version": self.VERSION,
        }
