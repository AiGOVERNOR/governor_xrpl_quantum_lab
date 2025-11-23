import json

from ecosystem.flow_engine import build_default_flow_engine
from ecosystem.tx.intents import TxIntent


def main():
    engine = build_default_flow_engine()

    # Demo intent for CPFE
    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
        destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
        metadata={"note": "flow_engine_demo"},
    )

    # Flow engine returns a dict (not an object)
    decision = engine.plan_flow(intent)

    # The fix: print the returned dict directly
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
