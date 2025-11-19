"""
Guardian – VQM Network Policy + Fee Pressure Intelligence

This module analyzes XRPL network_state and produces:
- Mesh-level mode (normal / fee_pressure / extreme_fee_pressure)
- A human-oriented LLM-style explanation (no external calls)
- A structured network_policy payload
- An AI VQM Fee Pressure Reducer plan (local-only mitigation)

NO transactions are submitted.
NO trading is performed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from ecosystem.telemetry import (
    classify_fee_band,
    make_guardian_attestation,
)
from ecosystem.fee_reducer import FeePressureReducer


@dataclass
class GuardianConfig:
    version: str = "1.3.0"  # Level-3+ with Fee Pressure Reducer
    attention_threshold_drops: int = 2000
    extreme_threshold_drops: int = 5000


class GuardianVQMPipeline:
    def __init__(self, config: GuardianConfig | None = None) -> None:
        self.config = config or GuardianConfig()
        self._fee_reducer = FeePressureReducer()

    @property
    def version(self) -> str:
        return self.config.version

    # ---------------------------
    # Core assessment
    # ---------------------------

    def assess(self, network_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point used by the orchestrator.

        Args:
            network_state: dict with:
              - ledger_seq
              - txn_base_fee
              - txn_median_fee
              - recommended_fee_drops
              - load_factor

        Returns:
            dict with keys:
              - mesh
              - policy
              - llm
              - forge
              - reducer
        """
        median = int(network_state.get("txn_median_fee", 10) or 10)
        load_factor = float(network_state.get("load_factor", 1.0) or 1.0)
        rec_fee = int(network_state.get("recommended_fee_drops", median) or median)

        band = classify_fee_band(median_fee_drops=median, load_factor=load_factor)
        band_label = band["band"]

        if median >= self.config.extreme_threshold_drops:
            mode = "extreme_fee_pressure"
            status = "attention_required"
        elif median >= self.config.attention_threshold_drops:
            mode = "fee_pressure"
            status = "attention_required"
        else:
            mode = "normal"
            status = "compliant"

        # Mesh view (compact)
        mesh_state = {
            "ledger": network_state.get("ledger_seq"),
            "load_factor": load_factor,
            "fee_drops": median,
            "mode": mode,
        }

        # Policy payload
        policy = {
            "id": self._make_policy_id(),
            "category": "network_policy",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "status": status,
            "payload": {
                "ledger": network_state.get("ledger_seq"),
                "load_factor": load_factor,
                "txn_base_fee": network_state.get("txn_base_fee"),
                "txn_median_fee": median,
                "recommended_fee": rec_fee,
                "fee_band": band,
            },
        }

        # Forge: what upgrades/improvements should the ecosystem consider?
        forge = self._build_forge(mode=mode, band=band, median=median)

        # LLM-style explanation (local, hand-written prompt-free)
        llm = self._build_llm_view(mode, network_state, band, policy)

        # Fee Pressure Reducer (local-only)
        reducer_plan = self._fee_reducer.build_plan(
            network_state=network_state,
            fee_band=band,
            guardian_policy=policy,
        )

        # Attestation (for logs / future auditors)
        attestation = make_guardian_attestation(
            network_state=network_state,
            mode=mode,
            recommended_fee=rec_fee,
            extra={"band": band, "reducer_mode": reducer_plan["mode"]},
        )

        return {
            "mesh": mesh_state,
            "policy": policy,
            "forge": forge,
            "llm": llm,
            "reducer": reducer_plan,
            "attestation": attestation,
        }

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _make_policy_id(self) -> str:
        # Simple time-based ID; no external libs.
        return datetime.now(timezone.utc).strftime("POLICY-%Y%m%d-%H%M%S-%f")

    def _build_forge(self, mode: str, band: Dict[str, Any], median: int) -> Dict[str, Any]:
        suggested_changes: list[str] = []

        if mode == "normal":
            suggested_changes.extend([
                "Maintain current fee bands; monitor for trend shifts.",
                "Consider enabling additional AI/VQM telemetry for research.",
            ])
        elif mode == "fee_pressure":
            suggested_changes.extend([
                "Tighten fee bands for non-essential flows.",
                "Prioritize essential, short-lived transactions.",
                "Review throughput limits on high-volume integrations.",
            ])
        else:  # extreme_fee_pressure
            suggested_changes.extend([
                "Freeze all non-critical protocol upgrades until fees stabilize.",
                "Evaluate whether certain flows can be re-timed to off-peak hours.",
                "Perform a deeper investigation into traffic sources correlated with spikes.",
            ])

        return {
            "status": "draft",
            "upgrade_id": self._make_policy_id(),
            "inferred_mode": mode,
            "fee_band": band,
            "suggested_changes": suggested_changes,
        }

    def _build_llm_view(
        self,
        mode: str,
        network_state: Dict[str, Any],
        band: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        median = int(network_state.get("txn_median_fee", 10) or 10)
        load_factor = float(network_state.get("load_factor", 1.0) or 1.0)
        rec_fee = int(network_state.get("recommended_fee_drops", median) or median)

        if mode == "normal":
            explanation = (
                f"Network appears healthy with median fee {median} drops and load_factor={load_factor}. "
                f"Fee band classified as '{band['band']}'. No special actions required beyond observation."
            )
        elif mode == "fee_pressure":
            explanation = (
                f"Fee pressure detected: median fees elevated to {median} drops at load_factor={load_factor}. "
                f"Band '{band['band']}' suggests prioritizing essential flows and tuning fee bands. "
                f"Recommended fee for planning is {rec_fee} drops."
            )
        else:
            explanation = (
                f"Extreme fee pressure detected: median={median} drops, load_factor={load_factor}, "
                f"band='{band['band']}'. Local systems should minimize their on-ledger footprint "
                f"and treat the situation as a temporary stress epoch."
            )

        return {
            "mode": mode,
            "explanation": explanation,
            "human_context": (
                f"Ledger {network_state.get('ledger_seq')}, "
                f"load_factor={load_factor}, "
                f"median_fee={median} drops, "
                f"recommended_fee={rec_fee} drops"
            ),
            "policy_id": policy["id"],
        }
