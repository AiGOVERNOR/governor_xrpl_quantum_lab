"""
XRPL RPC Layer – VQM Enhanced Edition
Self-healing, multi-node, websocket-enabled XRPL telemetry engine.
"""

import time
import json
import random
import requests
from typing import List, Dict, Any, Optional

try:
    from websocket import create_connection
    WEBSOCKET_AVAILABLE = True
except:
    WEBSOCKET_AVAILABLE = False


class XRPL_RPC:
    def __init__(
        self,
        rpc_nodes: Optional[List[str]] = None,
        ws_nodes: Optional[List[str]] = None,
        timeout: int = 10,
    ):
        self.rpc_nodes = rpc_nodes or [
            "https://s1.ripple.com:51234",
            "https://s2.ripple.com:51234",
            "https://xrplcluster.com"
        ]

        self.ws_nodes = ws_nodes or [
            "wss://xrplcluster.com",
            "wss://s1.ripple.com"
        ]

        self.timeout = timeout
        self.node_failures = {u: 0 for u in self.rpc_nodes}
        self.ws = None
        self.ws_active_node = None

        # EMA fee predictor
        self.ema_fee = None
        self.ema_alpha = 0.12

    # -------------------------
    #   Multi-node RPC core
    # -------------------------
    def _select_best_rpc(self) -> str:
        # Prefer nodes with fewer failures
        ranked = sorted(self.rpc_nodes, key=lambda u: self.node_failures[u])
        return ranked[0]

    def _rpc_call(self, method: str, params: dict | None = None) -> dict:
        url = self._select_best_rpc()
        try:
            payload = {"method": method, "params": [params or {}]}
            r = requests.post(url, json=payload, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()

            if "result" not in data:
                raise ValueError(f"Malformed RPC response: {data}")

            # Success: reset failure score
            self.node_failures[url] = 0
            return data["result"]

        except Exception:
            self.node_failures[url] += 1
            # Try next best node automatically
            return self._rpc_call(method, params)

    # -------------------------
    #   WebSocket Layer
    # -------------------------
    def _connect_ws(self):
        if not WEBSOCKET_AVAILABLE:
            return None

        for u in self.ws_nodes:
            try:
                ws = create_connection(u, timeout=self.timeout)
                self.ws_active_node = u
                self.ws = ws
                return ws
            except:
                continue
        return None

    def _ws_request(self, method: str) -> Optional[dict]:
        if not WEBSOCKET_AVAILABLE:
            return None

        if self.ws is None:
            self._connect_ws()

        if self.ws is None:
            return None

        try:
            self.ws.send(json.dumps({"command": method}))
            data = json.loads(self.ws.recv())
            return data

        except Exception:
            # Reconnect and retry once
            self._connect_ws()
            return None

    # -------------------------
    # Fee & network state
    # -------------------------
    def _read_fee_via_ws(self) -> Optional[dict]:
        msg = self._ws_request("fee")
        if not msg or "result" not in msg:
            return None
        return msg["result"]

    def fee(self) -> dict:
        # Prefer real-time WebSocket feed
        ws_data = self._read_fee_via_ws()
        if ws_data:
            return ws_data
        return self._rpc_call("fee")

    def _ema_predict(self, median: float) -> float:
        if self.ema_fee is None:
            self.ema_fee = median
        else:
            self.ema_fee = (
                self.ema_alpha * median + (1 - self.ema_alpha) * self.ema_fee
            )
        return round(self.ema_fee)

    # -------------------------
    #  Unified snapshot for VQM
    # -------------------------
    def get_fee_snapshot(self) -> dict:
        f = self.fee()
        drops = f.get("drops", {})

        ledger = f.get("ledger_current_index") or f.get("ledger_index") or 0

        base = int(drops.get("base_fee", drops.get("base_fee_drops", 10)))
        median = int(drops.get("median_fee", drops.get("median_fee_drops", base)))
        open_ledger = int(
            drops.get("open_ledger_fee", drops.get("open_ledger_fee_drops", median))
        )

        # Reject insane outliers (node bugs)
        if median > 1000000:
            median = base

        recommended = max(
            median,
            int(open_ledger * 1.3),
            self._ema_predict(median)
        )

        load_factor = float(f.get("load_factor", 1.0))

        return {
            "ledger_seq": int(ledger),
            "txn_base_fee": base,
            "txn_median_fee": median,
            "recommended_fee_drops": recommended,
            "load_factor": load_factor,
        }


