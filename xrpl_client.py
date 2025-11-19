import json
import time
from typing import Any, Dict, Optional

import requests


class XRPLClientError(Exception):
    """Generic XRPL client error."""


class XRPLClient:
    """
    Minimal XRPL JSON-RPC client.

    Default endpoint is a public Ripple server. You can later swap
    to your own node / Clio / XRPL sidechain.
    """

    def __init__(self, url: str = "https://s1.ripple.com:51234", timeout: int = 10):
        self.url = url
        self.timeout = timeout
        self._request_id = int(time.time())

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a raw JSON-RPC request to XRPL.

        Raises XRPLClientError if we get a non-200 HTTP or XRPL-side error.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": [params],
            "id": self._next_id(),
        }

        try:
            resp = requests.post(
                self.url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise XRPLClientError(f"HTTP error talking to XRPL: {e}") from e

        if resp.status_code != 200:
            raise XRPLClientError(f"Non-200 status {resp.status_code}: {resp.text}")

        data = resp.json()

        # XRPL servers (rippled / clio) usually wrap in 'result'
        result = data.get("result")
        if result is None:
            raise XRPLClientError(f"Unexpected XRPL response: {data}")

        if result.get("status") == "error":
            err = result.get("error", "unknownError")
            err_msg = result.get("error_message", "")
            raise XRPLClientError(f"XRPL error: {err} {err_msg}".strip())

        return result

    # -------- Convenience methods -------- #

    def ping(self) -> Dict[str, Any]:
        return self.request("ping", {})

    def server_info(self) -> Dict[str, Any]:
        return self.request("server_info", {})

    def account_info(self, account: str, strict: bool = True) -> Dict[str, Any]:
        return self.request(
            "account_info",
            {
                "account": account,
                "strict": strict,
                "ledger_index": "validated",
                "queue": True,
            },
        )

    def account_lines(self, account: str, ledger_index: str = "validated") -> Dict[str, Any]:
        return self.request(
            "account_lines",
            {
                "account": account,
                "ledger_index": ledger_index,
            },
        )

    def account_objects(self, account: str, ledger_index: str = "validated") -> Dict[str, Any]:
        return self.request(
            "account_objects",
            {
                "account": account,
                "ledger_index": ledger_index,
            },
        )

    def account_tx(
        self,
        account: str,
        limit: int = 10,
        ledger_index_min: int = -1,
        ledger_index_max: int = -1,
    ) -> Dict[str, Any]:
        return self.request(
            "account_tx",
            {
                "account": account,
                "ledger_index_min": ledger_index_min,
                "ledger_index_max": ledger_index_max,
                "limit": limit,
                "forward": False,
            },
        )

    def fee(self) -> Dict[str, Any]:
        return self.request("fee", {})

    def ledger(self, ledger_index: str = "validated") -> Dict[str, Any]:
        return self.request(
            "ledger",
            {
                "ledger_index": ledger_index,
                "accounts": False,
                "full": False,
                "transactions": False,
                "expand": False,
            },
        )

    def submit_tx_blob(self, tx_blob_hex: str) -> Dict[str, Any]:
        """
        Submit a pre-signed transaction blob (hex).

        NOTE: This does NOT sign. It just sends the blob.
        Signing will be done by a separate module / device.
        """
        return self.request(
            "submit",
            {
                "tx_blob": tx_blob_hex,
            },
        )


def main():
    """
    Tiny CLI for quick sanity checks:

        python xrpl_client.py ping
        python xrpl_client.py info
    """
    import argparse
    from rich import print as rprint

    parser = argparse.ArgumentParser(description="Minimal XRPL JSON-RPC client")
    parser.add_argument("command", choices=["ping", "info", "fee"], help="What to do")
    parser.add_argument("--url", default="https://s1.ripple.com:51234", help="XRPL JSON-RPC URL")
    args = parser.parse_args()

    client = XRPLClient(url=args.url)

    if args.command == "ping":
        rprint(client.ping())
    elif args.command == "info":
        rprint(client.server_info())
    elif args.command == "fee":
        rprint(client.fee())


if __name__ == "__main__":
    main()
