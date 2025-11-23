import json
from ecosystem.pipeline_v5 import run_vqm_cycle_v5
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.brain import tx_brain

def main() -> None:
    state = run_vqm_cycle_v5()
    net = state["network_state"]
    guardian_hint = state.get("guardian", {})

    intent = TxIntent.new(
        kind="simple_payment",
        amount_drops=1_000_000,
        source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
        destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
        metadata={"note": "tx_brain_demo"},
    )

    plan = tx_brain.plan_for_intent(intent, net, guardian_hint)
    print(json.dumps(plan, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
