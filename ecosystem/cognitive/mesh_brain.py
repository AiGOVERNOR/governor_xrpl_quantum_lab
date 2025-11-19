from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CognitiveSignal:
    """
    High-level inference over the recent VQM pipeline states.
    """
    global_mode: str
    volatility: float
    fee_trend: str
    guardian_modes: List[str]
    narrative: str
    scope: str = "xrpl_vqm_mesh"
    version: str = "0.1.0"


class CognitiveMeshBrain:
    """
    Tiny, local "brain" that reads recent history and emits a summarized
    global signal. This does NOT trade, sign, or mutate XRPL – it only
    observes and summarizes.
    """

    def analyze(self, history: List[Dict[str, Any]]) -> CognitiveSignal:
        if not history:
            return CognitiveSignal(
                global_mode="bootstrapping",
                volatility=0.0,
                fee_trend="unknown",
                guardian_modes=[],
                narrative="Cognitive mesh warming up; no history available yet.",
            )

        # --- extract recent slices ---
        last = history[-1]
        recent = history[-32:]  # last 32 cycles

        fees: List[int] = []
        loads: List[float] = []
        guardian_modes: List[str] = []

        for snap in recent:
            ns = snap.get("network_state") or {}
            fees.append(int(ns.get("txn_median_fee", 0)))
            loads.append(float(ns.get("load_factor", 0.0)))

            g = snap.get("guardian") or {}
            gm = (
                (g.get("mesh") or {}).get("mode")
                or (g.get("policy") or {}).get("mode")
            )
            if gm:
                guardian_modes.append(str(gm))

        if not fees:
            fees = [0]
        if not loads:
            loads = [0.0]

        current_fee = fees[-1]
        avg_fee = sum(fees) / len(fees)
        min_fee = min(fees)
        max_fee = max(fees)
        fee_span = max_fee - min_fee

        # crude volatility measure in [0, 1]
        volatility = 0.0
        if avg_fee > 0:
            volatility = min(1.0, fee_span / max(avg_fee, 1.0))

        # determine fee_trend
        if len(fees) >= 4:
            tail = fees[-4:]
            if tail[-1] > tail[0] * 1.25:
                fee_trend = "rising"
            elif tail[-1] < tail[0] * 0.75:
                fee_trend = "falling"
            else:
                fee_trend = "flat"
        else:
            fee_trend = "flat"

        # infer global mode
        guardian_modes_norm = [m or "unknown" for m in guardian_modes]
        mode_counts: Dict[str, int] = {}
        for m in guardian_modes_norm:
            mode_counts[m] = mode_counts.get(m, 0) + 1
        dominant_mode = max(mode_counts, key=mode_counts.get) if mode_counts else "unknown"

        if dominant_mode == "fee_pressure":
            if volatility > 0.5:
                global_mode = "fee_storm_watch"
            else:
                global_mode = "fee_pressure_watch"
        elif dominant_mode in ("normal", "steady_state"):
            if volatility < 0.3:
                global_mode = "steady_state"
            else:
                global_mode = "watchful"
        else:
            global_mode = "diagnostic"

        # build narrative
        narrative_parts = []

        narrative_parts.append(
            f"Current median fee {current_fee} drops "
            f"(avg={int(avg_fee)}, span={fee_span})."
        )

        if fee_trend == "rising":
            narrative_parts.append("Fees show a rising pattern over the last cycles.")
        elif fee_trend == "falling":
            narrative_parts.append("Fees show a falling pattern; pressure may be easing.")
        else:
            narrative_parts.append("Fees are roughly stable over the recent horizon.")

        if guardian_modes_norm:
            narrative_parts.append(
                f"Guardian dominant mode is '{dominant_mode}' "
                f"observed {mode_counts[dominant_mode]} times."
            )
        else:
            narrative_parts.append("Guardian has not yet emitted consistent modes.")

        if global_mode in ("fee_storm_watch", "fee_pressure_watch"):
            narrative_parts.append(
                "Cognitive Mesh recommends cautious capacity planning and keeping "
                "retail flows affordable via StreamPay + escrow protocols."
            )
        elif global_mode == "steady_state":
            narrative_parts.append(
                "Cognitive Mesh reports steady conditions; normal operations are appropriate."
            )
        else:
            narrative_parts.append(
                "Cognitive Mesh is in diagnostic mode; monitor telemetry and policies."
            )

        narrative = " ".join(narrative_parts)

        return CognitiveSignal(
            global_mode=global_mode,
            volatility=round(volatility, 3),
            fee_trend=fee_trend,
            guardian_modes=guardian_modes_norm[-8:],  # last few modes
            narrative=narrative,
        )
