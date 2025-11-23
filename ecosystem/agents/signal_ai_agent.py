#!/usr/bin/env python3
"""
signal_ai_agent.py
------------------
AI-style buy/sell signal generator.

Behavior:
 - Attempts to pull a real XRP price from an external API (Binance).
 - If price API fails, falls back to a synthetic random-walk price.
 - Uses a simple moving average crossover strategy.
 - Publishes BUY/SELL/HOLD signals to the message bus.

Later:
 - Swap in better data providers.
 - Replace strategy with more advanced logic or ML.
"""

import time
import random
from typing import List, Dict, Any, Optional

import requests

from . import message_bus


class SignalAIAgent:
    def __init__(
        self,
        symbol: str = "XRP",
        name: str = "signal_ai",
        use_external_price: bool = True,
    ):
        self.symbol = symbol
        self.name = name
        self.prices: List[float] = []
        self.max_len: int = 200

        # Simple MA windows
        self.short_window = 5
        self.long_window = 20

        self.last_signal: Optional[str] = None  # "BUY" | "SELL" | "HOLD"

        self.use_external_price = use_external_price

    # ------------------------------------------------------------
    # External price feed
    # ------------------------------------------------------------
    def _fetch_external_price(self) -> Optional[float]:
        """
        Fetch XRP price in USDT from Binance public API.
        Returns price as float or None on error.
        """
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": "XRPUSDT"}

        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            price_str = data.get("price")
            if price_str is None:
                return None
            return float(price_str)
        except Exception as e:
            print(f"[{self.name}] ERROR fetching external price: {e}")
            return None

    # ------------------------------------------------------------
    # Synthetic price feed (fallback)
    # ------------------------------------------------------------
    def _generate_synthetic_price(self) -> float:
        """
        Generate a pseudo-random walk price.
        Used as fallback if external feed fails.
        """
        if not self.prices:
            base = 0.50  # start at $0.50 arbitrarily
        else:
            base = self.prices[-1]

        step = random.uniform(-0.005, 0.005)
        new_price = max(0.1, base + step)
        return round(new_price, 4)

    def _get_price(self) -> float:
        """
        Try external feed first (if enabled).
        On failure, use synthetic price.
        """
        price: Optional[float] = None

        if self.use_external_price:
            price = self._fetch_external_price()

        if price is None:
            # Fallback
            price = self._generate_synthetic_price()
            print(f"[{self.name}] Using synthetic price: {price}")
        else:
            print(f"[{self.name}] Got external price: {price}")

        return price

    def update_price(self) -> float:
        price = self._get_price()
        self.prices.append(price)
        if len(self.prices) > self.max_len:
            self.prices = self.prices[-self.max_len :]
        return price

    # ------------------------------------------------------------
    # Strategy
    # ------------------------------------------------------------
    def _moving_average(self, window: int) -> Optional[float]:
        if len(self.prices) < window:
            return None
        window_slice = self.prices[-window:]
        return sum(window_slice) / len(window_slice)

    def generate_signal(self) -> Optional[Dict[str, Any]]:
        """
        Very simple MA crossover:
          - if short MA crosses above long MA -> BUY
          - if short MA crosses below long MA -> SELL
          - else HOLD
        """
        short_ma = self._moving_average(self.short_window)
        long_ma = self._moving_average(self.long_window)

        if short_ma is None or long_ma is None:
            return None

        if short_ma > long_ma * 1.001:  # tiny threshold
            signal = "BUY"
        elif short_ma < long_ma * 0.999:
            signal = "SELL"
        else:
            signal = "HOLD"

        if signal == self.last_signal:
            # no change; avoid spamming
            return None

        self.last_signal = signal

        return {
            "symbol": self.symbol,
            "signal": signal,
            "short_ma": short_ma,
            "long_ma": long_ma,
            "price": self.prices[-1],
            "ts": time.time(),
        }

    # ------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------
    def run(self, interval: int = 10) -> None:
        """
        Main loop. Every `interval` seconds:
          - fetch/update price
          - compute signal
          - publish if changed
        """
        print(
            f"[{self.name}] AI signal agent started for {self.symbol}. "
            f"use_external_price={self.use_external_price}"
        )

        while True:
            price = self.update_price()
            sig = self.generate_signal()
            if sig is not None:
                print(
                    f"[{self.name}] {sig['signal']} @ {sig['price']} "
                    f"(short={sig['short_ma']:.4f}, long={sig['long_ma']:.4f})"
                )
                message_bus.publish_message(
                    sender=self.name,
                    msg_type="trade_signal",
                    payload=sig,
                )

            time.sleep(interval)


if __name__ == "__main__":
    agent = SignalAIAgent(symbol="XRP", name="signal_ai", use_external_price=True)
    try:
        agent.run(interval=10)
    except KeyboardInterrupt:
        print("[signal_ai] Exiting.")
