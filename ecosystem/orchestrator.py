from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from xrpl_rpc import XRPL_RPC
from ecosystem.guardian import guardian_cycle

# Optional infra pieces: orchestrator must run even if these are missing.
try:
    from ecosystem.telemetry import TelemetryStore  # type: ignore
except Exception:
    TelemetryStore = None  # type: ignore

try:
    from ecosystem.pipelines.episodes import EpisodeDetector  # type: ignore
except Exception:
    EpisodeDetector = None  # type: ignore

try:
    from ecosystem.tools import ToolRegistry  # type: ignore
except Exception:
    ToolRegistry = None  # type: ignore


DATA_DIR = Path("data")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_network_state(snap: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize whatever XRPL_RPC.get_fee_snapshot() returns into
    a consistent, Guardian-friendly structure.
    """
    return {
        "ledger_seq": snap.get("ledger_seq"),
        "txn_base_fee": snap.get("txn_base_fee"),
        "txn_median_fee": snap.get("txn_median_fee"),
        "recommended_fee_drops": snap.get("recommended_fee_drops"),
        "load_factor": snap.get("load_factor"),
    }


def _init_tool_registry() -> Optional["ToolRegistry"]:
    if ToolRegistry is None:
        return None

    registry = ToolRegistry.load_default(DATA_DIR)

    # Seed known tools that already exist in your ecosystem.
    registry.ensure_tool(
        "fee_vqm_tool",
        category="fee",
        metadata={"description": "Dynamic XRPL fee band advisor."},
    )
    registry.ensure_tool(
        "stream_pay_tool",
        category="payment_protocol",
        metadata={"description": "XRPL StreamPay (salary/stream) protocol logic."},
    )
    registry.ensure_tool(
        "escrow_milestone_tool",
        category="escrow",
        metadata={"description": "Milestone escrow protocol planner."},
    )
    registry.ensure_tool(
        "fee_pressure_reducer",
        category="network_policy",
        metadata={"description": "AI-guided fee pressure reduction advisor."},
    )

    return registry


def run_vqm_cycle() -> Dict[str, Any]:
    """
    Single VQM cycle:

    1. Read XRPL fee/network state via XRPL_RPC.
    2. Run Guardian + AI Fee Pressure Reducer.
    3. Append telemetry snapshot to JSONL log (best-effort).
    4. Optionally:
       - maintain tool scores,
       - detect last fee-pressure episode from telemetry.

    Returns a JSON-safe dict used by:
    - ecosystem.cli.governor_cli
    - FastAPI / uvicorn API if you wire it.
    """
    rpc = XRPL_RPC()
    fee_snapshot = rpc.get_fee_snapshot()

    network_state = _build_network_state(fee_snapshot)

    guardian_state = guardian_cycle(network_state)

    state: Dict[str, Any] = {
        "network_state": network_state,
        "guardian": guardian_state,
        "pipeline_version": "1.4.0",  # bumped for infra+episodes+tools
        "timestamp": _iso_now(),
    }

    # ---------- Telemetry logging ----------
    telemetry_store = None
    if TelemetryStore is not None:
        telemetry_store = TelemetryStore(DATA_DIR / "xrpl_vqm_telemetry.log")
        telemetry_store.append(state)
        telemetry_store.rotate_if_needed()

    # ---------- Tool registry ----------
    if ToolRegistry is not None:
        registry = _init_tool_registry()
        if registry is not None:
            registry.update_from_guardian(guardian_state)
            registry.save()
            state["tools"] = registry.as_export()

    # ---------- Episode detection ----------
    if EpisodeDetector is not None and telemetry_store is not None:
        detector = EpisodeDetector()
        # Pull a modest window; enough to catch a recent episode
        recent = list(telemetry_store.iter_recent(max_lines=256))
        episode = detector.detect_last_episode(recent)
        if episode is not None:
            state["last_fee_pressure_episode"] = {
                "mode": episode.mode,
                "start_ledger": episode.start_ledger,
                "end_ledger": episode.end_ledger,
                "start_time": episode.start_time,
                "end_time": episode.end_time,
                "median_fee": episode.median_fee,
                "load_factor": episode.load_factor,
                "length": len(episode.snapshots),
            }

    return state
