"""
XRPL RPC Layer – VQM Level 2 Intelligence
-----------------------------------------
Multi-node, websocket-aware, fee-smart, telemetry-rich RPC adapter
for the VQM ecosystem. Safe, read-only, and mainnet-friendly.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

import requests

try:
    from websocket import create_connection
    WEBSOCKET_AVAILABLE = True
except Exception:
    WEBSOCKET_AVAILABLE = False

from ecosystem.telemetry import (
    compute_ledger_rate,
    classify_fee_band,
    make_guardian_attestation,
)


class XRPL_RPC:
    """
    High-res XRPL observer.

    Features:
    - Multi-node JSON-RPC with failure-aware routing.
    - Optional WebSocket feed for real-time fees.
    - EMA-based fee smoothing and outlier rejection.
    - Ledger close rate estimates (LPS / seconds-per-ledger).
    - Fee band classification (low / normal / elevated / extreme).
    - Attestation builder for Guardian/VQM pipelines.
    """

    def __init__(
        self,
        rpc_nodes: Optional[List[str]] = None,
        ws_nodes: Optional[List[str]] = None,
        timeout: int = 10,
        federation_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        # Multi-node setup
        self.rpc_nodes = rpc_nodes or [
            "https://s1.ripple.com:51234",
            "https://s2.ripple.com:51234",
            "https://xrplcluster.com",
        ]
        self.ws_nodes = ws_nodes or [
            "wss://xrplcluster.com",
            "wss://s1.ripple.com",
        ]
        self.timeout = timeout

        self.node_failures: Dict[str, int] = {u: 0 for u in self.rpc_nodes}

        # WebSocket state
        self.ws = None
        self.ws_active_node: Optional[str] = None

        # Fee predictor state
        self.ema_fee: Optional[float] = None
        self.ema_alpha: float = 0.12

        # Ledger rate state
        self.prev_ledger_seq: Optional[int] = None
        self.prev_ledger_ts: Optional[float] = None

        # Federation metadata (optional)
        self.federation_id = federation_id
        self.node_id = node_id

    # ------------------------------------------------------------------
    # Core RPC routing
    # ------------------------------------------------------------------
    def _select_best_rpc(self) -> str:
        """
        Picks the node with the fewest recorded failures.
        """
        ranked = sorted(self.rpc_nodes, key=lambda u: self.node_failures[u])
        return ranked[0]

    def _rpc_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simple JSON-RPC wrapper with failure-aware node rotation.
        """
        url = self._select_best_rpc()
        payload = {"method": method, "params": [params or {}]}

        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if "result" not in data:
                raise ValueError(f"Malformed RPC response from {url}: {data!r}")

            # On success, clear failure counter.
            self.node_failures[url] = 0
            return data["result"]

        except Exception:
            # Mark node as failing and try again on the next one.
            self.node_failures[url] += 1

            # If all nodes are failing, just raise the last exception.
            if all(v > 0 for v in self.node_failures.values()):
                raise
            return self._rpc_call(method, params)

    # ------------------------------------------------------------------
    # WebSocket handling
    # ------------------------------------------------------------------
    def _connect_ws(self):
        """
        Lazy WebSocket connect to the first node that works.
        """
        if not WEBSOCKET_AVAILABLE:
            return None

        for u in self.ws_nodes:
            try:
                ws = create_connection(u, timeout=self.timeout)
                self.ws_active_node = u
                self.ws = ws
                return ws
            except Exception:
                continue
        self.ws = None
        self.ws_active_node = None
        return None

    def _ws_request(self, command: str) -> Optional[Dict[str, Any]]:
        if not WEBSOCKET_AVAILABLE:
            return None

        if self.ws is None:
            self._connect_ws()
        if self.ws is None:
            return None

        try:
            self.ws.send(json.dumps({"command": command}))
            raw = self.ws.recv()
            data = json.loads(raw)
            return data
        except Exception:
            # Reconnect once; give up if it still fails
            self._connect_ws()
            return None

    # ------------------------------------------------------------------
    # Raw fee / state calls
    # ------------------------------------------------------------------
    def _fee_via_ws(self) -> Optional[Dict[str, Any]]:
        msg = self._ws_request("fee")
        if not msg or "result" not in msg:
            return None
        return msg["result"]

    def fee(self) -> Dict[str, Any]:
        """
        Public: get the XRPL 'fee' result, preferring WebSockets but
        falling back to RPC when needed.
        """
        ws_data = self._fee_via_ws()
        if ws_data:
            return ws_data
        return self._rpc_call("fee")

    def server_info(self) -> Dict[str, Any]:
        """
        Optional diagnostics about the node we are seeing.
        """
        return self._rpc_call("server_info")

    # ------------------------------------------------------------------
    # EMA and fee shaping
    # ------------------------------------------------------------------
    def _ema_predict(self, median: float) -> int:
        """
        Exponentially weighted moving average of median fees, to
        dampen spikes and smooth policy decisions.
        """
        if self.ema_fee is None:
            self.ema_fee = median
        else:
            self.ema_fee = (
                self.ema_alpha * median + (1.0 - self.ema_alpha) * self.ema_fee
            )
        return int(round(self.ema_fee))

    # ------------------------------------------------------------------
    # Level 2: unified snapshot (backwards compatible)
    # ------------------------------------------------------------------
    def get_fee_snapshot(self) -> Dict[str, Any]:
        """
        Main entry point for VQM / Guardian.

        Returns a dict with at least:
          - ledger_seq
          - txn_base_fee
          - txn_median_fee
          - recommended_fee_drops
          - load_factor

        Plus additional Level 2 fields:
          - ledger_rate: {ledgers_per_second, seconds_per_ledger}
          - fee_band: {band, comment}
          - server_diagnostics: (best-effort node info)
        """
        raw_fee = self.fee()
        drops = raw_fee.get("drops", {})

        ledger = raw_fee.get
cat > xrpl_rpc.py << 'EOF'
"""
XRPL RPC Layer – VQM Level 2 Intelligence
-----------------------------------------
Multi-node, websocket-aware, fee-smart, telemetry-rich RPC adapter
for the VQM ecosystem. Safe, read-only, and mainnet-friendly.
"""


import json
import time
from typing import Any, Dict, List, Optional

import requests

try:
    from websocket import create_connection
    WEBSOCKET_AVAILABLE = True
except Exception:
    WEBSOCKET_AVAILABLE = False

from ecosystem.telemetry import (
    compute_ledger_rate,
    classify_fee_band,
    make_guardian_attestation,
)


class XRPL_RPC:
    """
    High-res XRPL observer.

    Features:
    - Multi-node JSON-RPC with failure-aware routing.
    - Optional WebSocket feed for real-time fees.
    - EMA-based fee smoothing and outlier rejection.
    - Ledger close rate estimates (LPS / seconds-per-ledger).
    - Fee band classification (low / normal / elevated / extreme).
    - Attestation builder for Guardian/VQM pipelines.
    """

    def __init__(
        self,
        rpc_nodes: Optional[List[str]] = None,
        ws_nodes: Optional[List[str]] = None,
        timeout: int = 10,
        federation_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        # Multi-node setup
        self.rpc_nodes = rpc_nodes or [
            "https://s1.ripple.com:51234",
            "https://s2.ripple.com:51234",
            "https://xrplcluster.com",
        ]
        self.ws_nodes = ws_nodes or [
            "wss://xrplcluster.com",
            "wss://s1.ripple.com",
        ]
        self.timeout = timeout

        self.node_failures: Dict[str, int] = {u: 0 for u in self.rpc_nodes}

        # WebSocket state
        self.ws = None
        self.ws_active_node: Optional[str] = None

        # Fee predictor state
        self.ema_fee: Optional[float] = None
        self.ema_alpha: float = 0.12

        # Ledger rate state
        self.prev_ledger_seq: Optional[int] = None
        self.prev_ledger_ts: Optional[float] = None

        # Federation metadata (optional)
        self.federation_id = federation_id
        self.node_id = node_id

    # ------------------------------------------------------------------
    # Core RPC routing
    # ------------------------------------------------------------------
    def _select_best_rpc(self) -> str:
        """
        Picks the node with the fewest recorded failures.
        """
        ranked = sorted(self.rpc_nodes, key=lambda u: self.node_failures[u])
        return ranked[0]

    def _rpc_call(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Simple JSON-RPC wrapper with failure-aware node rotation.
        """
        url = self._select_best_rpc()
        payload = {"method": method, "params": [params or {}]}

        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if "result" not in data:
                raise ValueError(f"Malformed RPC response from {url}: {data!r}")

            # On success, clear failure counter.
            self.node_failures[url] = 0
            return data["result"]

        except Exception:
            # Mark node as failing and try again on the next one.
            self.node_failures[url] += 1

            # If all nodes are failing, just raise the last exception.
            if all(v > 0 for v in self.node_failures.values()):
                raise
            return self._rpc_call(method, params)

    # ------------------------------------------------------------------
    # WebSocket handling
    # ------------------------------------------------------------------
    def _connect_ws(self):
        """
        Lazy WebSocket connect to the first node that works.
        """
        if not WEBSOCKET_AVAILABLE:
            return None

        for u in self.ws_nodes:
            try:
                ws = create_connection(u, timeout=self.timeout)
                self.ws_active_node = u
                self.ws = ws
                return ws
            except Exception:
                continue
        self.ws = None
        self.ws_active_node = None
        return None

    def _ws_request(self, command: str) -> Optional[Dict[str, Any]]:
        if not WEBSOCKET_AVAILABLE:
            return None

        if self.ws is None:
            self._connect_ws()
        if self.ws is None:
            return None

        try:
            self.ws.send(json.dumps({"command": command}))
            raw = self.ws.recv()
            data = json.loads(raw)
            return data
        except Exception:
            # Reconnect once; give up if it still fails
            self._connect_ws()
            return None

    # ------------------------------------------------------------------
    # Raw fee / state calls
    # ------------------------------------------------------------------
    def _fee_via_ws(self) -> Optional[Dict[str, Any]]:
        msg = self._ws_request("fee")
        if not msg or "result" not in msg:
            return None
        return msg["result"]

    def fee(self) -> Dict[str, Any]:
        """
        Public: get the XRPL 'fee' result, preferring WebSockets but
        falling back to RPC when needed.
        """
        ws_data = self._fee_via_ws()
        if ws_data:
            return ws_data
        return self._rpc_call("fee")

    def server_info(self) -> Dict[str, Any]:
        """
        Optional diagnostics about the node we are seeing.
        """
        return self._rpc_call("server_info")

    # ------------------------------------------------------------------
    # EMA and fee shaping
    # ------------------------------------------------------------------
    def _ema_predict(self, median: float) -> int:
        """
        Exponentially weighted moving average of median fees, to
        dampen spikes and smooth policy decisions.
        """
        if self.ema_fee is None:
            self.ema_fee = median
        else:
            self.ema_fee = (
                self.ema_alpha * median + (1.0 - self.ema_alpha) * self.ema_fee
            )
        return int(round(self.ema_fee))

    # ------------------------------------------------------------------
    # Level 2: unified snapshot (backwards compatible)
    # ------------------------------------------------------------------
    def get_fee_snapshot(self) -> Dict[str, Any]:
        """
        Main entry point for VQM / Guardian.

        Returns a dict with at least:
          - ledger_seq
          - txn_base_fee
          - txn_median_fee
          - recommended_fee_drops
          - load_factor

        Plus additional Level 2 fields:
          - ledger_rate: {ledgers_per_second, seconds_per_ledger}
          - fee_band: {band, comment}
          - server_diagnostics: (best-effort node info)
        """
        raw_fee = self.fee()
        drops = raw_fee.get("drops", {})

        ledger = raw_fee.get("ledger_current_index") or raw_fee.get("ledger_index") or 0
        ledger_seq = int(ledger)

        base = int(drops.get("base_fee", drops.get("base_fee_drops", 10)))
        median = int(drops.get("median_fee", drops.get("median_fee_drops", base)))
        open_ledger = int(
            drops.get(
                "open_ledger_fee",
                drops.get("open_ledger_fee_drops", median),
            )
        )

        # Outlier protection: if some node returns nonsense, clamp.
        if median > 1_000_000:
            median = base

        # Core recommended fee: respect open-ledger pressure + EMA
        ema_pred = self._ema_predict(median)
        recommended = max(
            median,
            int(open_ledger * 1.3),
            ema_pred,
        )

        load_factor = float(raw_fee.get("load_factor", 1.0))

        # Ledger rate estimation (L2)
        now_ts = time.time()
        rate = compute_ledger_rate(
            current_seq=ledger_seq,
            current_ts=now_ts,
            prev_seq=self.prev_ledger_seq,
            prev_ts=self.prev_ledger_ts,
        )
        self.prev_ledger_seq = ledger_seq
        self.prev_ledger_ts = now_ts

        # Fee band classification (L2)
        band = classify_fee_band(
            base_drops=base,
            median_drops=median,
            recommended_drops=recommended,
        )

        # Server diagnostics (best-effort, non-fatal)
        server_diag: Dict[str, Any] = {}
        try:
            info = self.server_info()
            server_state = info.get("info", {})
            server_diag = {
                "pubkey_node": server_state.get("pubkey_node"),
                "complete_ledgers": server_state.get("complete_ledgers"),
                "validation_quorum": server_state.get("validation_quorum"),
                "server_state": server_state.get("server_state"),
                "server_version": server_state.get("build_version"),
                "peers": server_state.get("peers"),
            }
        except Exception:
            server_diag = {}

        snapshot: Dict[str, Any] = {
            # Level 1 (original contract)
            "ledger_seq": ledger_seq,
            "txn_base_fee": base,
            "txn_median_fee": median,
            "recommended_fee_drops": recommended,
            "load_factor": load_factor,
        }

        # Level 2 enrichments
        snapshot["ledger_rate"] = {
            "ledgers_per_second": rate.ledgers_per_second,
            "seconds_per_ledger": rate.seconds_per_ledger,
        }
        snapshot["fee_band"] = {
            "band": band.band,
            "comment": band.comment,
        }
        snapshot["server_diagnostics"] = server_diag

        return snapshot

    # ------------------------------------------------------------------
    # Level 2: Guardian attestation helper
    # ------------------------------------------------------------------
    def build_attestation(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wraps the current snapshot in an unsigned attestation document
        that can be logged, shipped, or later signed.
        """
        return make_guardian_attestation(
            snapshot=snapshot,
            federation_id=self.federation_id,
            node_id=self.node_id,
        )
