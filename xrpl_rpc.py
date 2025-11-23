"""
xrpl_rpc.py

Tiny XRPL JSON-RPC client used by the governor_xrpl_quantum_lab.

Goals:
- LIVE data from a public XRPL endpoint (fees + ledger index).
- Zero signing / submission: READ-ONLY ONLY.
- Safe, defensive, and "self-healing":
  - If the remote node fails, fall back to a static snapshot.
  - Always return a consistent dict shape that network_state expects.

This module is intentionally dependency-light: it uses only the Python
standard library (urllib + json + ssl).
"""

from __future__ import annotations

import json
import os
import ssl
import time
from typing import Any, Dict, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Public XRPL JSON-RPC endpoint.
# You can override this via environment variable XRPL_RPC_ENDPOINT.
XRPL_RPC_ENDPOINT = os.getenv("XRPL_RPC_ENDPOINT", "https://xrplcluster.com")

# Network timeout in seconds for HTTP calls.
XRPL_RPC_TIMEOUT = float(os.getenv("XRPL_RPC_TIMEOUT", "5.0"))

# ---------------------------------------------------------------------------
# Low-level HTTP JSON-RPC helper
# ---------------------------------------------------------------------------


def _post_json(method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Perform a JSON-RPC POST to the XRPL endpoint.

    Returns the "result" field from the RPC response.

    Raises RuntimeError on network or protocol errors, so callers can
    decide whether to fall back to a static snapshot.
    """
    if params is None:
        params = {}

    payload = {
        "method": method,
        "params": [params],
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    req = Request(XRPL_RPC_ENDPOINT, data=data, headers=headers)

    # Create a modern TLS context.
    ctx = ssl.create_default_context()

    try:
        with urlopen(req, context=ctx, timeout=XRPL_RPC_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:  # type: ignore[name-defined]
        raise RuntimeError(f"XRPL RPC network error for method={method}: {exc}") from exc

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"XRPL RPC JSON decode error for method={method}: {exc}") from exc

    if not isinstance(decoded, dict) or "result" not in decoded:
        raise RuntimeError(f"XRPL RPC unexpected response shape for method={method}: {decoded}")

    result = decoded["result"]
    if not isinstance(result, dict):
        raise RuntimeError(f"XRPL RPC 'result' field is not an object for method={method}: {result}")

    return result


# ---------------------------------------------------------------------------
# Static fallback snapshot (self-healing mode)
# ---------------------------------------------------------------------------


def _static_fee_snapshot() -> Dict[str, Any]:
    """
    Local fallback used when the XRPL JSON-RPC call fails.

    This keeps the rest of the engine running in "simulation mode"
    instead of crashing. The values are conservative defaults.
    """
    # Use a fake but monotonic ledger index so downstream code that
    # expects a positive ledger_seq doesn't break.
    fake_ledger_seq = int(time.time())

    base_fee = 10
    median_fee = 5000
    recommended_fee = median_fee
    open_ledger_fee = median_fee
    load_factor = 1.0

    return {
        "ledger_seq": fake_ledger_seq,
        "load_factor": load_factor,
        "base_fee_drops": base_fee,
        "median_fee_drops": median_fee,
        "recommended_fee_drops": recommended_fee,
        "open_ledger_fee_drops": open_ledger_fee,
    }


# ---------------------------------------------------------------------------
# High-level helpers expected by ecosystem.network_state
# ---------------------------------------------------------------------------


def get_fee_snapshot() -> Dict[str, Any]:
    """
    Main entry point used by ecosystem.network_state.

    Returns a dict with at least:
      - ledger_seq: int
      - load_factor: float
      - base_fee_drops: int
      - median_fee_drops: int
      - recommended_fee_drops: int
      - open_ledger_fee_drops: int

    On network / RPC failure, falls back to a static local snapshot.
    """
    try:
        result = _post_json("fee", {})
    except RuntimeError:
        # Self-healing: network is down or endpoint misbehaving.
        # Fall back to static defaults so the rest of the engine still works.
        return _static_fee_snapshot()

    drops = result.get("drops", {}) or {}
    validated_ledger = result.get("validated_ledger", {}) or {}

    # Ledger index: try several known locations.
    ledger_seq = 0
    if "ledger_current_index" in result:
        ledger_seq = int(result["ledger_current_index"])
    elif "ledger_index" in result:
        ledger_seq = int(result["ledger_index"])
    elif "seq" in validated_ledger:
        ledger_seq = int(validated_ledger["seq"])

    # Fee drops.
    # XRPL "fee" method commonly returns these fields under "drops".
    base_fee = int(drops.get("base_fee", "10"))
    median_fee = int(drops.get("median_fee", drops.get("minimum_fee", base_fee)))
    open_ledger_fee = int(drops.get("open_ledger_fee", median_fee))

    # We treat "median" as the recommended operating fee.
    recommended_fee = median_fee

    # Load factor (if available); otherwise default to 1.0.
    load_factor = float(result.get("load_factor", 1.0))

    return {
        "ledger_seq": ledger_seq,
        "load_factor": load_factor,
        "base_fee_drops": base_fee,
        "median_fee_drops": median_fee,
        "recommended_fee_drops": recommended_fee,
        "open_ledger_fee_drops": open_ledger_fee,
    }


# ---------------------------------------------------------------------------
# Backwards-compatible helper aliases
# ---------------------------------------------------------------------------


def get_fee() -> Dict[str, Any]:
    """
    Backwards-compatible helper.

    Returns a minimal dict with:
      - fee_drops
      - ledger_seq
      - load_factor

    Some legacy code paths may look for this instead of get_fee_snapshot().
    """
    snap = get_fee_snapshot()
    return {
        "fee_drops": snap["recommended_fee_drops"],
        "ledger_seq": snap["ledger_seq"],
        "load_factor": snap["load_factor"],
    }


def get_fees() -> Dict[str, Any]:
    """
    Alias to get_fee_snapshot(), for older helper naming schemes.
    """
    return get_fee_snapshot()


def get_fee_and_ledger() -> Tuple[int, int]:
    """
    Another compatibility helper: return (ledger_seq, recommended_fee_drops).
    """
    snap = get_fee_snapshot()
    return snap["ledger_seq"], snap["recommended_fee_drops"]
