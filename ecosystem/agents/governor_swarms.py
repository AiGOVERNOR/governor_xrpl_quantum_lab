#!/usr/bin/env python3
"""
governor_swarms.py
------------------
Top-level orchestrator for the Governor XRPL Quantum Lab swarm.

Runs:
 - AetherbornSwarm (wallet monitor → wallet_balance_change events)
 - SignalAIAgent (buy/sell signals, using external price if possible)
 - LiquidityAgent (acts on trade_signal messages)
"""

import threading
import time

from ecosystem.agents.aetherborn_swarm import AetherbornSwarm
from ecosystem.agents.signal_ai_agent import SignalAIAgent
from ecosystem.agents.liquidity_agent import LiquidityAgent


PUBLIC_WALLET = "rEXdG3Rh9Ejb3NKXoxb16xge4d3BHskJUP"
RPC_URL = "https://s1.ripple.com:51234"


def start_aetherborn():
    agent = AetherbornSwarm(
        rpc_url=RPC_URL,
        public_wallet=PUBLIC_WALLET,
        name="aetherborn",
    )
    agent.start(interval=5)
    # Keep this thread alive
    while True:
        time.sleep(1)


def start_signal_ai():
    agent = SignalAIAgent(
        symbol="XRP",
        name="signal_ai",
        use_external_price=True,
    )
    agent.run(interval=10)


def start_liquidity():
    agent = LiquidityAgent(name="liquidity_agent")
    agent.run(poll_interval=0.5)


def main():
    threads = []

    t1 = threading.Thread(target=start_aetherborn, daemon=True)
    t2 = threading.Thread(target=start_signal_ai, daemon=True)
    t3 = threading.Thread(target=start_liquidity, daemon=True)

    threads.extend([t1, t2, t3])

    for t in threads:
        t.start()

    print("[governor_swarms] Swarm orchestrator running. Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[governor_swarms] Exiting.")


if __name__ == "__main__":
    main()
