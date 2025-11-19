from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests

from .models import (
    NetworkState,
    GuardianSnapshot,
    FeeHorizon,
    MeshIntentSnapshot,
    VQMFullState,
)


class VQMClientError(Exception):
    """Base exception for the VQM Integrators SDK."""


class VQMClient:
    """
    Thin client for querying a running VQM API node.

    Assumes your FastAPI app (api_vqm:app) exposes at least:

        GET /v1/state

    which returns a JSON body similar to:

        {
          "network_state": {...},
          "guardian": {...},
          "fee_horizon": {...},
          "mesh_intent": {...},
          "tools": [...],
          "pipeline_version": "...",
          "timestamp": "..."
        }

    All methods are read-only and side-effect-free on XRPL.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ---------- low-level HTTP ----------

    def _request(self, method: str, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(method, url, timeout=self.timeout)
        except Exception as exc:
            raise VQMClientError(f"Request to {url} failed: {exc}") from exc

        if not resp.ok:
            raise VQMClientError(
                f"HTTP {resp.status_code} from {url}: {resp.text[:300]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise VQMClientError(
                f"Non-JSON response from {url}: {resp.text[:300]}"
            ) from exc

    # ---------- core API ----------

    def get_full_state_raw(self) -> Dict[str, Any]:
        """
        Get the raw /v1/state JSON as a Python dict.
        """
        return self._request("GET", "/v1/state")

    def get_full_state(self) -> VQMFullState:
        """
        Get a structured view of /v1/state.
        """
        raw = self.get_full_state_raw()

        ns_raw = raw.get("network_state", {}) or {}
        network_state = NetworkState(
            ledger_seq=int(ns_raw.get("ledger_seq", 0)),
            txn_base_fee=int(ns_raw.get("txn_base_fee", 0)),
            txn_median_fee=int(ns_raw.get("txn_median_fee", 0)),
            recommended_fee_drops=int(ns_raw.get("recommended_fee_drops", 0)),
            load_factor=float(ns_raw.get("load_factor", 0.0)),
        )

        guardian_raw = raw.get("guardian")
        guardian: Optional[GuardianSnapshot]
        if guardian_raw is None:
            guardian = None
        else:
            mode = (
                guardian_raw.get("mesh", {}).get("mode")
                or guardian_raw.get("policy", {}).get("mode")
                or "unknown"
            )
            policy_status = (
                guardian_raw.get("policy", {}).get("status")
                or guardian_raw.get("policy", {}).get("policy_status")
            )
            explanation = guardian_raw.get("llm", {}).get("explanation")
            guardian = GuardianSnapshot(
                mode=mode,
                policy_status=policy_status,
                explanation=explanation,
                raw=guardian_raw,
            )

        fee_raw = raw.get("fee_horizon")
        fee_horizon: Optional[FeeHorizon]
        if fee_raw is None:
            fee_horizon = None
        else:
            band = fee_raw.get("projected_fee_band") or fee_raw.get("band") or "unknown"
            horizon_seconds = int(fee_raw.get("horizon_seconds", 0))
            ts = fee_raw.get("trend_short", {})
            tl = fee_raw.get("trend_long", {})
            trend_short = ts.get("direction") if isinstance(ts, dict) else str(ts)
            trend_long = tl.get("direction") if isinstance(tl, dict) else str(tl)
            fee_horizon = FeeHorizon(
                band=band,
                horizon_seconds=horizon_seconds,
                trend_short=trend_short,
                trend_long=trend_long,
                raw=fee_raw,
            )

        mi_raw = raw.get("mesh_intent")
        mesh_intent: Optional[MeshIntentSnapshot]
        if mi_raw is None:
            mesh_intent = None
        else:
            mode = mi_raw.get("mode", "unknown")
            priority = mi_raw.get("priority", "unknown")
            band = (
                mi_raw.get("schedule_ref", {}).get("band")
                or mi_raw.get("inputs", {}).get("band")
                or "unknown"
            )
            mesh_intent = MeshIntentSnapshot(
                mode=mode,
                priority=priority,
                band=band,
                raw=mi_raw,
            )

        tools = raw.get("tools") or []

        return VQMFullState(
            pipeline_version=str(raw.get("pipeline_version", "")),
            timestamp=str(raw.get("timestamp", "")),
            network_state=network_state,
            guardian=guardian,
            fee_horizon=fee_horizon,
            mesh_intent=mesh_intent,
            tools=tools,
            raw=raw,
        )

    # ---------- convenience helpers ----------

    def get_network_state(self) -> NetworkState:
        return self.get_full_state().network_state

    def get_guardian(self) -> Optional[GuardianSnapshot]:
        return self.get_full_state().guardian

    def get_fee_horizon(self) -> Optional[FeeHorizon]:
        return self.get_full_state().fee_horizon

    def get_mesh_intent(self) -> Optional[MeshIntentSnapshot]:
        return self.get_full_state().mesh_intent

    def get_tools(self) -> List[Dict[str, Any]]:
        return self.get_full_state().tools

    # ---------- diagnostics ----------

    def ping(self) -> bool:
        """
        Simple health check. If /v1/state responds successfully, returns True.
        """
        try:
            self.get_full_state_raw()
            return True
        except VQMClientError:
            return False
