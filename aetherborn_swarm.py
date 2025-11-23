#!/usr/bin/env python3
"""
Aetherborn Swarm Agent
----------------------
Primary agent node for the Governor XRPL Quantum Lab.
Handles:
 - Wallet state
 - XRPL balance monitoring
 - Pathfinding
 - Lightweight task routing
 - Swarm messaging hooks
"""

import time
import json
import threading
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo
from xrpl.wallet import Wallet


class AetherbornSwarm:
    """
    Aetherborn Swarm: A semi-autonomous XRPL agent.
    Lightweight, modular, and designed to plug into
    ALL other governor agents and liquidity fabrics.
    """

    def __init__(self, rpc_url, public_wallet):
        self.rpc = JsonRpcClient(rpc_url)
        self.wallet_address = public_wallet
        self._stop_signal = False

        # Runtime state
        self.last_balance = None
        self.last_update_time = None

    # ------------------------------------------------------------
    # XRPL Account Monitor
    # ------------------------------------------------------------
    def get_balance(self):
        """Query XRP balance in drops → convert to XRP"""
        try:
            req = AccountInfo(
                account=self.wallet_address,
                ledger_index="validated",
                strict=True,
            )
            response = self.rpc.request(req)

            if "account_data" not in response.result:
                return None

            drops = int(response.result["account_data"]["Balance"])
            return drops / 1_000_000  # convert drops → XRP
        except Exception as e:
            return f"[ERROR] get_balance(): {e}"

    # ------------------------------------------------------------
    # Live Monitor Loop
    # ------------------------------------------------------------
    def monitor_balance(self, interval=5):
        """
        Watches the wallet in real-time.
        Emits events when balance changes.
        """
        print(f"[AETHERBORN] Monitoring {self.wallet_address} every {interval}s…")

        while not self._stop_signal:
            new_balance = self.get_balance()
            self.last_update_time = time.time()

            if new_balance != self.last_balance:
                print(f"[AETHERBORN] Balance update: {new_balance} XRP")
                self.last_balance = new_balance
                self.on_balance_change(new_balance)

            time.sleep(interval)

        print("[AETHERBORN] Monitor loop stopped.")

    # ------------------------------------------------------------
    # Event Hooks
    # ------------------------------------------------------------
    def on_balance_change(self, new_balance):
        """
        Hook for auto-behavior when funds appear.
        Replace/expand with logic (AMM, swaps, routing, etc.)
        """
        print(f"[EVENT] Wallet balance changed → {new_balance} XRP")

    # ------------------------------------------------------------
    # Thread Controls
    # ------------------------------------------------------------
    def start(self):
        """Start monitoring in a background thread."""
        self._stop_signal = False
        t = threading.Thread(target=self.monitor_balance)
        t.daemon = True
        t.start()
        print("[AETHERBORN] Swarm agent started.")

    def stop(self):
        """Stop monitoring."""
        self._stop_signal = True
        print("[AETHERBORN] Stopping agent…")

    # ------------------------------------------------------------
    # Debug / Status
    # ------------------------------------------------------------
    def status(self):
        return {
            "wallet": self.wallet_address,
            "last_balance": self.last_balance,
            "last_update_time": self.last_update_time,
        }


# =====================================================================
# DIRECT RUNTIME (executed only when running this file directly)
# =====================================================================

if __name__ == "__main__":
    # --- SET YOUR PUBLIC WALLET HERE ---
    PUBLIC_WALLET = "rEXdG3Rh9Ejb3NKXoxb16xge4d3BHskJUP"

    agent = AetherbornSwarm(
        rpc_url="https://s1.ripple.com:51234",
        public_wallet=PUBLIC_WALLET,
    )

    agent.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
        print("[AETHERBORN] Exiting.")
