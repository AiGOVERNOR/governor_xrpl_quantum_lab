#!/usr/bin/env python3
"""
liquidity_agent.py
------------------
Consumes trade_signal messages and decides what to do.

Behavior:
 - Listens on message bus for `trade_signal`.
 - Logs what it *would* do (BUY/SELL) with size based on simple rules.
 - Publishes a follow-up `liquidity_action` message.

Optional:
 - If LIVE_TRADING = True, attempts to place a real XRPL trade
   (requires secret key + more config).
"""

import os
import time
from typing import Dict, Any, Optional

from xrpl.clients import JsonRpcClient
from xrpl.transaction import (
    safe_sign_and_autofill_transaction,
    send_reliable_submission,
)
from xrpl.wallet import Wallet
from xrpl.models.transactions import Payment
from xrpl.models.amounts import IssuedCurrencyAmount

from . import message_bus


# ------------------------------------------------------------
# Global config – tweak here
# ------------------------------------------------------------
RPC_URL = "https://s1.ripple.com:51234"
LIVE_TRADING = False  # *** SAFETY SWITCH: KEEP FALSE UNTIL READY ***
BASE_CURRENCY = "XRP"  # what we trade from


class LiquidityAgent:
    def __init__(self, name: str = "liquidity_agent"):
        self.name = name
        self.offset = message_bus.count_messages()

        # XRPL client
        self.client = JsonRpcClient(RPC_URL)

        # Wallet – secret from env, to avoid hardcoding
        self.seed = os.environ.get("XRPL_SECRET")
        self.wallet: Optional[Wallet] = None

        if LIVE_TRADING:
            if not self.seed:
                print(
                    f"[{self.name}] LIVE_TRADING enabled but XRPL_SECRET "
                    "not set. Trading will NOT proceed."
                )
            else:
                self.wallet = Wallet(seed=self.seed, sequence=0)
                print(f"[{self.name}] LIVE_TRADING enabled for {self.wallet.classic_address}")
        else:
            print(f"[{self.name}] Running in DRY-RUN mode (no real trades).")

    # ------------------------------------------------------------
    # Core handling
    # ------------------------------------------------------------
    def handle_trade_signal(self, msg: Dict[str, Any]) -> None:
        payload = msg["payload"]
        symbol = payload.get("symbol", "XRP")
        signal = payload.get("signal", "HOLD")
        price = payload.get("price")
        short_ma = payload.get("short_ma")
        long_ma = payload.get("long_ma")

        print(
            f"[{self.name}] Received trade_signal: {signal} {symbol} @ {price} "
            f"(short={short_ma:.4f}, long={long_ma:.4f})"
        )

        if signal == "HOLD":
            return

        # Placeholder size logic – you’ll eventually map this to real risk mgmt.
        size_units = 10.0

        action = {
            "symbol": symbol,
            "side": signal,  # BUY or SELL
            "size_units": size_units,
            "price": price,
            "ts": time.time(),
        }

        if LIVE_TRADING and self.wallet is not None:
            self._execute_trade(action)
        else:
            print(
                f"[{self.name}] DRY-RUN: would {signal} {size_units} {symbol} @ {price}"
            )

        # Publish the intended/attempted action to bus
        message_bus.publish_message(
            sender=self.name,
            msg_type="liquidity_action",
            payload=action,
        )

    # ------------------------------------------------------------
    # XRPL trade execution stub
    # ------------------------------------------------------------
    def _execute_trade(self, action: Dict[str, Any]) -> None:
        """
        VERY SIMPLE PAYMENT STUB.
        This is NOT a full DEX/AMM trade engine, just a placeholder:
          - If BUY: send BASE_CURRENCY (XRP) to some counterparty in exchange
                    for IOU (not fully implemented)
          - If SELL: send IOU to counterparty to receive XRP.

        You must customize issuer, destination, and pathing for real usage.
        """
        if not self.wallet:
            print(f"[{self.name}] Cannot trade: no wallet loaded.")
            return

        side = action.get("side")
        symbol = action.get("symbol", "XRP")
        size_units = float(action.get("size_units", 0))
        price = float(action.get("price", 0))

        print(
            f"[{self.name}] LIVE_TRADING STUB: {side} {size_units} {symbol} @ {price}"
        )

        # Example: send a tiny test XRP payment to yourself (as a placeholder).
        # In real trading, you'd construct OfferCreate or AMMDeposit/Withdraw
        # transactions instead.
        if symbol == "XRP" and side in ("BUY", "SELL"):
            try:
                payment = Payment(
                    account=self.wallet.classic_address,
                    amount=str(int(size_units * 1_000_000)),  # XRP → drops
                    destination=self.wallet.classic_address,
                )
                signed = safe_sign_and_autofill_transaction(
                    payment, self.wallet, self.client
                )
                tx_resp = send_reliable_submission(signed, self.client)
                print(f"[{self.name}] Submitted XRPL payment tx: {tx_resp.result}")
            except Exception as e:
                print(f"[{self.name}] ERROR executing XRPL stub payment: {e}")
        else:
            print(
                f"[{self.name}] No real trade logic implemented for {side} {symbol}. "
                "Extend _execute_trade with DEX/AMM logic."
            )

    # ------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------
    def run(self, poll_interval: float = 1.0) -> None:
        print(f"[{self.name}] Liquidity agent starting from offset {self.offset}.")

        stream = message_bus.consume_messages_from(self.offset)
        for msg in stream:
            self.offset += 1
            if msg.get("type") == "trade_signal":
                self.handle_trade_signal(msg)
            time.sleep(poll_interval)


if __name__ == "__main__":
    agent = LiquidityAgent(name="liquidity_agent")
    try:
        agent.run()
    except KeyboardInterrupt:
        print("[liquidity_agent] Exiting.")
