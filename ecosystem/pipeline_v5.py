"""
ecosystem.pipeline_v5
---------------------
VQM Pipeline v5: adds quantum telemetry, fee trend analysis,
anomaly detection, and scheduler advice on top of the base
VQM + Guardian pipeline.

SAFE: read-only, mainnet-compatible, no signing, no trading.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ecosystem.orchestrator import run_vqm_cycle
from ecosystem.scheduler import Scheduler
from ecosystem.telemetry import (
    compute_ledger_rate,
    classify_fee_band,
    anomaly_detect,
    predict_fee_trend,
)


class VQMPipelineV5:
    """
    High-level orchestrator for the VQM brain (v5).

    Responsibilities:
    - Call base VQM+Guardian cycle.
    - Maintain short histories (median_fee, ledger_seq).
    - Compute fee band, trends, anomalies.
    - Provide scheduler advice.
    """

    def __init__(self) -> None:
        # History buffers (in-memory only, short windows)
        self._median_fee_history: List[int] = []
        self._ledger_history: List[int] = []

        # Scheduler instance
        self._scheduler = Scheduler()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _update_histories(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update median fee and ledger histories from the latest state.
        Returns a normalized snapshot of the core network fields.
        """
        net = state.get("network_state", {}) or {}

        ledger_seq = int(net.get("ledger_seq", 0) or 0)
        median_fee = int(net.get("txn_median_fee", 0) or 0)
        base_fee = int(net.get("txn_base_fee", 0) or 0)
        load_factor = float(net.get("load_factor", 0.0) or 0.0)
        recommended_fee = int(net.get("recommended_fee_drops", median_fee) or 0)

        # Update histories (bounded)
        if median_fee > 0:
            self._median_fee_history.append(median_fee)
            self._median_fee_history = self._median_fee_history[-50:]

        if ledger_seq > 0:
            self._ledger_history.append(ledger_seq)
            self._ledger_history = self._ledger_history[-50:]

        return {
            "ledger_seq": ledger_seq,
            "txn_base_fee": base_fee,
            "txn_median_fee": median_fee,
            "recommended_fee_drops": recommended_fee,
            "load_factor": load_factor,
        }

    def _build_fee_horizon(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the fee_horizon block using telemetry helpers.
        """
        median_fee = int(snapshot.get("txn_median_fee", 0) or 0)
        load_factor = float(snapshot.get("load_factor", 0.0) or 0.0)

        # Telemetry helpers all expect LISTS, not dicts.
        # Use internal histories we maintain.
        ledger_rate = compute_ledger_rate(self._ledger_history)
        band_info = classify_fee_band(median_fee=median_fee, load_factor=load_factor)
        trend_info = predict_fee_trend(self._median_fee_history)
        anomaly_info = anomaly_detect(self._median_fee_history)

        horizon: Dict[str, Any] = {
            "model_version": "0.1.0",
            "horizon_seconds": 600,  # conceptual horizon
            "projected_fee_band": band_info.get("band", "unknown"),
            "band_comment": band_info.get("comment", ""),
            "trend_short": {
                "direction": trend_info.get("trend", "flat"),
                "slope": 0.0,
            },
            "trend_long": {
                "direction": trend_info.get("trend", "flat"),
                "slope": 0.0,
            },
            "anomaly": anomaly_info,
            "ledger_rate": ledger_rate,
        }
        return horizon

    def _build_scheduler_block(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask the Scheduler for concurrency/job advice, based on current band.
        """
        median_fee = int(snapshot.get("txn_median_fee", 0) or 0)
        load_factor = float(snapshot.get("load_factor", 0.0) or 0.0)
        # We recompute the band here to stay consistent with fee_horizon.
        band_info = classify_fee_band(median_fee=median_fee, load_factor=load_factor)
        band = band_info.get("band", "normal")

        schedule = self._scheduler.plan(
            band=band,
            median_fee=median_fee,
            load_factor=load_factor,
        )

        return schedule

    # ------------------------------------------------------------------
    # Public entrypoint
    # ------------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """
        Run a full VQM v5 cycle:

        1. Call base VQM+Guardian orchestrator.
        2. Update internal histories.
        3. Compute fee_horizon + scheduler blocks.
        4. Return enriched state.
        """
        # 1) base state from v4/orchestrator
        base_state = run_vqm_cycle()

        # 2) normalize & update histories
        core_snapshot = self._update_histories(base_state)

        # 3) telemetry blocks
        fee_horizon = self._build_fee_horizon(core_snapshot)
        scheduler_block = self._build_scheduler_block(core_snapshot)

        # 4) attach and return enriched state
        enriched: Dict[str, Any] = dict(base_state)  # shallow copy
        enriched["network_state"] = core_snapshot
        enriched["fee_horizon"] = fee_horizon
        enriched["scheduler"] = scheduler_block
        enriched["pipeline_version"] = "1.7.0"

        return enriched


# Singleton pipeline instance used by CLIs and the API
_pipeline_v5 = VQMPipelineV5()


def run_vqm_cycle_v5() -> Dict[str, Any]:
    """
    Convenience function used by:
      - ecosystem.cli.tx_brain_cli
      - api_vqm, etc.

    Always returns a dict with at least:
      - network_state
      - fee_horizon
      - scheduler
      - (plus whatever base run_vqm_cycle adds, like guardian/tools)
    """
    return _pipeline_v5.run()
