from typing import Any, Dict, List, Optional


def _extract_median_fees(history: List[Dict[str, Any]]) -> List[int]:
    fees: List[int] = []
    for item in history:
        ns = item.get("network_state") or {}
        fee = ns.get("txn_median_fee") or ns.get("median_fee")
        if isinstance(fee, (int, float)):
            fees.append(int(fee))
    return fees


def _safe_avg(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def _compute_slope(values: List[float]) -> float:
    """
    Very simple slope: last - first over length.
    """
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / float(len(values) - 1)


def _direction_from_slope(slope: float, eps: float = 1e-6) -> str:
    if slope > eps:
        return "up"
    if slope < -eps:
        return "down"
    return "flat"


def _band_for_fee(median_fee: int) -> str:
    """
    Simple, self-contained fee banding heuristic.

    You can tune these thresholds to better reflect real-world conditions.
    """
    if median_fee <= 20:
        return "low"
    if median_fee <= 200:
        return "normal"
    if median_fee <= 2000:
        return "elevated"
    return "extreme"


def build_fee_horizon(
    history: List[Dict[str, Any]],
    current_network_state: Dict[str, Any],
    horizon_seconds: int = 600,
) -> Dict[str, Any]:
    """
    Construct a forward-looking "fee horizon" object based on recent history.

    Returns:
      {
        "horizon_seconds": int,
        "model_version": "str",
        "projected_fee_band": "low|normal|elevated|extreme",
        "trend_short": {direction, slope},
        "trend_long": {direction, slope},
        "comment": "string"
      }
    """
    median_fees = _extract_median_fees(history)
    current_median = int(
        current_network_state.get("txn_median_fee")
        or current_network_state.get("median_fee")
        or 10
    )

    # Short window: last 10 observations; Long: last 50.
    short_vals = [float(x) for x in median_fees[-10:]]
    long_vals = [float(x) for x in median_fees[-50:]]

    short_slope = _compute_slope(short_vals)
    long_slope = _compute_slope(long_vals)

    short_dir = _direction_from_slope(short_slope)
    long_dir = _direction_from_slope(long_slope)

    projected_band = _band_for_fee(current_median)

    if not median_fees:
        comment = (
            "Warm-up phase: not enough history; projecting band from current "
            "median fee only."
        )
    else:
        comment = (
            "Fee horizon derived from recent history; short trend="
            f"{short_dir}, long trend={long_dir}."
        )

    return {
        "horizon_seconds": horizon_seconds,
        "model_version": "0.2.0",
        "projected_fee_band": projected_band,
        "trend_short": {
            "direction": short_dir,
            "slope": short_slope,
        },
        "trend_long": {
            "direction": long_dir,
            "slope": long_slope,
        },
        "comment": comment,
    }
