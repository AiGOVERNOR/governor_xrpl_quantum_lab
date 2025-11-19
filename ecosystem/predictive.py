"""
Level 4: Predictive Fee Horizon for VQM Ecosystem.

Lightweight, in-process time-series logic that watches XRPL median fees
and produces a short- and long-horizon trend view. No external deps,
no ML libraries – just sane math and common sense.
"""

import time
from collections import deque
from typing import Deque, Dict, Any, List, Optional


class FeeHorizonModel:
    """
    Maintains a rolling history of XRPL network_state snapshots and
    derives a predictive "fee horizon" signal.

    Input shape (network_state dict, from orchestrator):
        {
            "ledger_seq": int,
            "txn_base_fee": int,
            "txn_median_fee": int,
            "recommended_fee_drops": int,
            "load_factor": float,
            ...
        }
    """

    def __init__(self, max_points: int = 120, horizon_seconds: int = 600) -> None:
        self._history: Deque[Dict[str, Any]] = deque(maxlen=max_points)
        self.horizon_seconds = horizon_seconds

    # --- internal helpers -------------------------------------------------

    def _as_point(self, network_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return {
                "ts": time.time(),
                "ledger_seq": int(network_state.get("ledger_seq", 0)),
                "median_fee": int(network_state.get("txn_median_fee", 0)),
                "recommended_fee": int(network_state.get("recommended_fee_drops", 0)),
                "load_factor": float(network_state.get("load_factor", 1.0)),
            }
        except Exception:
            # If anything is malformed, skip this point instead of breaking the pipeline.
            return None

    def _direction_from_slope(self, slope: float, eps: float = 1e-3) -> str:
        if slope > eps:
            return "rising"
        if slope < -eps:
            return "falling"
        return "flat"

    def _compute_slope(self, series: List[Dict[str, Any]]) -> float:
        """
        Very simple slope: delta(median_fee) / delta(time_seconds).
        """
        if len(series) < 2:
            return 0.0
        first = series[0]
        last = series[-1]
        dt = max(last["ts"] - first["ts"], 1e-6)
        df = float(last["median_fee"] - first["median_fee"])
        return df / dt

    # --- public API -------------------------------------------------------

    def update_and_forecast(self, network_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add latest network_state to history and return a fee_horizon dict:

        {
            "model_version": "0.1.0",
            "horizon_seconds": 600,
            "trend_short": { "slope": float, "direction": "rising|falling|flat" },
            "trend_long":  { ... },
            "projected_fee_band": "low|normal|elevated|extreme",
            "comment": "human friendly string",
        }
        """
        point = self._as_point(network_state)
        if point is None:
            # Nothing to do, but keep the pipeline alive.
            return {
                "model_version": "0.1.0",
                "horizon_seconds": self.horizon_seconds,
                "trend_short": {"slope": 0.0, "direction": "flat"},
                "trend_long": {"slope": 0.0, "direction": "flat"},
                "projected_fee_band": "unknown",
                "comment": "Insufficient or invalid data for prediction.",
            }

        self._history.append(point)

        # Not enough history yet
        if len(self._history) < 3:
            direction = "flat"
            return {
                "model_version": "0.1.0",
                "horizon_seconds": self.horizon_seconds,
                "trend_short": {"slope": 0.0, "direction": direction},
                "trend_long": {"slope": 0.0, "direction": direction},
                "projected_fee_band": "normal",
                "comment": "Warm-up phase: not enough history, assuming normal band.",
            }

        history_list = list(self._history)
        # Short horizon = last ~10 points, or all of them if fewer.
        short_window = history_list[-10:] if len(history_list) > 10 else history_list
        long_window = history_list

        slope_short = self._compute_slope(short_window)
        slope_long = self._compute_slope(long_window)

        dir_short = self._direction_from_slope(slope_short)
        dir_long = self._direction_from_slope(slope_long)

        median_now = point["median_fee"]

        # Very simple projected band rule:
        #   - If both slopes rising and median already high -> elevated/extreme.
        #   - If both falling -> normal/low.
        #   - Else -> keep current classification "normal".
        if median_now >= 5000 and dir_short == "rising" and dir_long == "rising":
            projected_band = "extreme"
            comment = "Fees already high and rising – extreme pressure likely."
        elif median_now >= 5000 and (dir_short == "rising" or dir_long == "rising"):
            projected_band = "elevated"
            comment = "Fees high with upward pressure – elevated band projected."
        elif median_now <= 12 and dir_short == "falling" and dir_long == "falling":
            projected_band = "low"
            comment = "Fees low and falling – low band projected."
        else:
            projected_band = "normal"
            comment = "Mixed signals – treating as normal band for safety."

        return {
            "model_version": "0.1.0",
            "horizon_seconds": self.horizon_seconds,
            "trend_short": {
                "slope": slope_short,
                "direction": dir_short,
            },
            "trend_long": {
                "slope": slope_long,
                "direction": dir_long,
            },
            "projected_fee_band": projected_band,
            "comment": comment,
        }
