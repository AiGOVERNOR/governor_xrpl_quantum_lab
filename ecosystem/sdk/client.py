import json
from typing import Any, Dict

import requests  # type: ignore

from ecosystem.pipeline_v5 import run_vqm_cycle_v5
from ecosystem.sdk.models import VQMClientConfig, VQMState


class VQMClient:
    """
    VQM Integrators SDK client.

    Design rules:
    - Read-only: never builds or submits transactions.
    - No trading: only observes network + guardian state.
    - Thin: small surface area, easy to embed anywhere.
    """

    def __init__(self, config: VQMClientConfig | None = None) -> None:
        self.config = config or VQMClientConfig()

    # ---------------------------
    # Internal fetch primitives
    # ---------------------------
    def _fetch_local(self) -> Dict[str, Any]:
        """
        Call the in-process pipeline_v5 directly.
        """
        return run_vqm_cycle_v5()

    def _fetch_http(self) -> Dict[str, Any]:
        """
        Call a remote VQM API (e.g. api_vqm.py) via HTTP.
        Expects a /vqm/state endpoint returning pipeline_v5 JSON.
        """
        assert self.config.base_url is not None
        url = self.config.base_url.rstrip("/") + "/vqm/state"
        resp = requests.get(url, timeout=self.config.timeout_seconds)
        resp.raise_for_status()
        return resp.json()

    def _fetch_raw(self) -> Dict[str, Any]:
        if self.config.mode == "local":
            return self._fetch_local()
        return self._fetch_http()

    # ---------------------------
    # Public API
    # ---------------------------
    def get_state(self) -> VQMState:
        """
        Run a VQM cycle and return a structured state object.
        """
        raw = self._fetch_raw()
        return VQMState(
            network_state=raw.get("network_state", {}),
            guardian=raw.get("guardian", {}),
            heartbeat=raw.get("heartbeat", {}),
            pipeline_version=raw.get("pipeline_version", "unknown"),
        )

    def get_network_state(self) -> Dict[str, Any]:
        """
        Convenience: just the XRPL network snapshot.
        """
        return self.get_state().network_state

    def get_guardian_state(self) -> Dict[str, Any]:
        """
        Convenience: guardian decision + safety info.
        """
        return self.get_state().guardian

    def get_safety_summary(self) -> Dict[str, Any]:
        """
        Convenience: compact safety-focused view.
        """
        return self.get_state().safety_summary()

    def pretty_print(self) -> None:
        """
        Dump the full VQM state to stdout (integrator-friendly).
        """
        state = self.get_state()
        out = {
            "pipeline_version": state.pipeline_version,
            "network_state": state.network_state,
            "guardian": state.guardian,
            "heartbeat": state.heartbeat,
        }
        print(json.dumps(out, indent=2, sort_keys=True))
