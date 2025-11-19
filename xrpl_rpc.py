"""
XRPL_RPC — Direct XRPL mainnet client for the VQM Ecosystem.
Safe. Read-only. Fully compliant with XRPL mainnet rules.
"""

import requests


class XRPL_RPC:
    def __init__(self, url="https://s1.ripple.com:51234"):
        self.url = url

    def _rpc(self, method: str, params=None):
        if params is None:
            params = {}

        payload = {
            "method": method,
            "params": [params],
        }

        response = requests.post(self.url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()["result"]

    # -------------------------------------------------------
    # NETWORK TELEMETRY
    # -------------------------------------------------------

    def fee(self):
        """XRPL fee endpoint."""
        return self._rpc("fee")

    def server_info(self):
        """XRPL server_info endpoint."""
        return self._rpc("server_info")

    def get_fee_summary(self):
        """Combines fee + server_info into one unified result."""
        fee_info = self.fee()
        drops = fee_info.get("drops", {})

        base = int(drops.get("base_fee", drops.get("base_fee_drops", "10")))
        median = int(drops.get("median_fee", str(base)))
        open_ledger = int(drops.get("open_ledger_fee", str(median)))

        recommended = max(median, int(open_ledger * 1.2))

        server = self.server_info()
        ledger_seq = server.get("info", {}).get("validated_ledger", {}).get("seq", 0)
        load = server.get("info", {}).get("load_factor", 1.0)

        return {
            "ledger_seq": ledger_seq,
            "txn_base_fee": base,
            "txn_median_fee": median,
            "recommended_fee_drops": recommended,
            "load_factor": load,
        }
