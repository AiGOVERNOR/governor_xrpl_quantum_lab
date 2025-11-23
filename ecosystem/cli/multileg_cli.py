# ecosystem/cli/multileg_cli.py

"""
Demo CLI for Multi-Leg Engine
"""

import json
from ecosystem.tx.intents import TxIntent
from ecosystem.multileg import build_default_multileg_engine


def main():
    engine = build_default_multileg_engine()

    intents = [
        TxIntent.new(
            kind="simple_payment",
            amount_drops=1_000_000,
            source_account="rSOURCE1",
            destination_account="rDEST1",
            metadata={"memo": "leg1"}
        ),
        TxIntent.new(
            kind="simple_payment",
            amount_drops=2_000_000,
            source_account="rSOURCE2",
            destination_account="rDEST2",
            metadata={"memo": "leg2"}
        )
    ]

    bundle = engine.plan_bundle(intents)
    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
