from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Literal
from uuid import uuid4


GuardianMode = Literal["calm", "normal", "fee_pressure", "stress", "attack"]


@dataclass
class GuardianPolicy:
    """
    A small, serializable description of the guardian's view
    of the current XRPL network condition.
    """

    id: str
    category: str
    mode: GuardianMode
    created_at: str
    status: str
    payload: Dict[str, Any]


@dataclass
class GuardianForgeResult:
    """
    A "what to change" suggestion set. This is NOT executable
    by itself – just a structured draft for human / higher-level
    review.
    """

    upgrade_id: str
    status: str
    inferred_mode: GuardianMode
    suggested_changes: list[str]


class XRPLGuardian:
    """
    XRPL VQM Guardian

    Reads a fee/network snapshot and classifies the XRPL into one of:
    - calm
    - normal
    - fee_pressure
    - stress
    - attack

    Then produces:
    - policy: guardian's formal stance
    - llm: human-facing explanation stub
    - forge: structured suggestions for infra / protocol tuning

    This class is intentionally *pure* and *stateless*:
    it just transforms an input snapshot into a JSON-friendly dict.
    """

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ---------- classification ----------

    def classify_mode(self, snapshot: Dict[str, Any]) -> GuardianMode:
        """
        Map a raw XRPL fee snapshot into a qualitative regime.
        """

        load_factor = float(snapshot.get("load_factor", 1.0))
        median_fee = int(snapshot.get("txn_median_fee", 10))
        base_fee = int(snapshot.get("txn_base_fee", 10))

        # Extremely high fee or load: assume attack or severe stress.
        if load_factor >= 5.0 or median_fee >= 20_000:
            return "attack"

        # Strong stress region where fees and load are elevated.
        if load_factor >= 3.0 or median_fee >= 10_000:
            return "stress"

        # Noticeable fee pressure for ordinary users.
        if median_fee >= 5_000:
            return "fee_pressure"

        # Very relaxed: low load and median close to base.
        if load_factor <= 1.0 and median_fee <= base_fee * 2:
            return "calm"

        # Catch-all default.
        return "normal"

    # ---------- policy + explanation ----------

    def _build_policy(self, mode: GuardianMode, snapshot: Dict[str, Any]) -> GuardianPolicy:
        policy_id = str(uuid4())

        payload = {
            "ledger": snapshot.get("ledger_seq"),
            "load_factor": snapshot.get("load_factor"),
            "recommended_fee": snapshot.get("recommended_fee_drops"),
            "txn_base_fee": snapshot.get("txn_base_fee"),
            "txn_median_fee": snapshot.get("txn_median_fee"),
        }

        status = "compliant"
        if mode in ("fee_pressure", "stress", "attack"):
            status = "attention_required"

        return GuardianPolicy(
            id=policy_id,
            category="network_policy",
            mode=mode,
            created_at=self._now_iso(),
            status=status,
            payload=payload,
        )

    def _build_llm_stub(self, mode: GuardianMode, snapshot: Dict[str, Any], policy: GuardianPolicy) -> Dict[str, Any]:
        """
        Human-facing explanation stub; in a real system this could be the
        prompt + summary basis for an LLM, but here it's just structured
        text for observability.
        """

        ledger = snapshot.get("ledger_seq")
        load_factor = snapshot.get("load_factor")
        median_fee = snapshot.get("txn_median_fee")
        rec_fee = snapshot.get("recommended_fee_drops")

        if mode == "calm":
            explanation = (
                "XRPL appears calm: low load, fees near base. "
                "Safe to keep standard policies; monitor for drift."
            )
        elif mode == "normal":
            explanation = (
                "XRPL in normal regime: healthy throughput with ordinary fees. "
                "No aggressive adjustments required."
            )
        elif mode == "fee_pressure":
            explanation = (
                "Fee pressure detected: median fees elevated. "
                "Recommend adjusting retail fee bands and prioritizing essential flows."
            )
        elif mode == "stress":
            explanation = (
                "Network stress regime: load and/or fees significantly elevated. "
                "Throttle non-essential flows and increase monitoring."
            )
        else:  # attack
            explanation = (
                "Severe regime (possible attack or extreme congestion). "
                "Restrict non-essential activity and enforce conservative policies."
            )

        return {
            "policy_id": policy.id,
            "mode": mode,
            "explanation": explanation,
            "human_context": (
                f"Ledger {ledger}, load_factor={load_factor}, "
                f"median_fee={median_fee} drops, recommended_fee={rec_fee} drops"
            ),
        }

    # ---------- forge suggestions ----------

    def _build_forge(self, mode: GuardianMode, snapshot: Dict[str, Any]) -> GuardianForgeResult:
        suggestions: list[str]

        if mode == "calm":
            suggestions = [
                "Maintain current fee bands.",
                "Consider experimenting with new retail/payment protocols.",
            ]
        elif mode == "normal":
            suggestions = [
                "Incrementally optimize protocol parameters.",
                "Keep fee bands aligned with observed median.",
            ]
        elif mode == "fee_pressure":
            suggestions = [
                "Tighten fee band for non-essential flows.",
                "Prefer simple/short-lived transactions over complex ones.",
                "Review throughput caps on heavy users/integrations.",
            ]
        elif mode == "stress":
            suggestions = [
                "Throttle low-priority flows.",
                "Increase safety margins on all protocol parameters.",
                "Raise minimum recommended fee for optional flows.",
            ]
        else:  # attack
            suggestions = [
                "Enter defensive mode: only essential/payment-critical traffic.",
                "Elevate minimum fees to discourage spam.",
                "Increase monitoring and alerting thresholds.",
            ]

        return GuardianForgeResult(
            upgrade_id=str(uuid4()),
            status="draft",
            inferred_mode=mode,
            suggested_changes=suggestions,
        )

    # ---------- public API ----------

    def guard(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point.

        Input:
          snapshot: dict with fields like:
            - ledger_seq
            - txn_base_fee
            - txn_median_fee
            - recommended_fee_drops
            - load_factor

        Output:
          {
            "mesh": {...},
            "policy": {...},
            "llm": {...},
            "forge": {...}
          }
        """

        mode = self.classify_mode(snapshot)
        policy = self._build_policy(mode, snapshot)
        llm_stub = self._build_llm_stub(mode, snapshot, policy)
        forge = self._build_forge(mode, snapshot)

        mesh_view = {
            "ledger": snapshot.get("ledger_seq"),
            "load_factor": snapshot.get("load_factor"),
            "fee_drops": snapshot.get("recommended_fee_drops"),
            "mode": mode,
        }

        return {
            "mesh": mesh_view,
            "policy": asdict(policy),
            "llm": llm_stub,
            "forge": asdict(forge),
        }
