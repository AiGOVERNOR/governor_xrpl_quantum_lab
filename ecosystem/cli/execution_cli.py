"""
ecosystem.cli.execution_cli
---------------------------
Demo CLI for the Quantum Execution Layer (QXL).

Flow:
  1. Build FlowEngine (CPFE)
  2. Plan a simple_payment intent
  3. Feed the flow_decision into QuantumExecutionEngine
  4. Print the execution bundle as JSON
"""

import json

from ecosystem.flow_engine import build_default_flow_engine
from ecosystem.tx.intents import TxIntent
from ecosystem.execution import QuantumExecutionEngine


def main() -> None:
    # 1) Build flow engine
    engine = build_default_flow_engine()

    # 2) Sample intent (still demo / placeholder accounts)
    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,  # 1 XRP in drops
        source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
        destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
        metadata={"note": "qxl_demo"},
    )

    # 3) FlowEngine decides protocol / routing / quantum / guardian context
    flow_decision = engine.plan_flow(intent)

    # 4) QXL wraps this into an execution bundle
    qxl = QuantumExecutionEngine()
    bundle = qxl.build_from_flow(flow_decision)

    print(json.dumps(bundle, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
