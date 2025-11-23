"""
CLI: Transaction Router V3 demo.
Shows:
  - VQM network_state
  - Guardian hint
  - Protocol plan
  - Router V3 decision
"""

import json

from ecosystem.pipeline_v5 import run_vqm_cycle_v5
from ecosystem.tx.intents import TxIntent
from ecosystem.tx.brain import tx_brain
from ecosystem.router_v3 import router_v3


def main() -> None:
    # Pull pipeline snapshot
    state = run_vqm_cycle_v5()
    net = state["network_state"]
    guardian_hint = state.get("guardian")

    # Build a sample intent
    intent = TxIntent.simple_payment(
        amount_drops=1_000_000,
        source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
        destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
        note="router_v3 demo payment",
    )

    # Ask Transaction Brain for protocol plan
    protocol_plan = tx_brain.plan_for_intent(intent, net, guardian_hint)

    # Ask Router V3 for a decision
    decision = router_v3.route(
        intent=intent,
        protocol_plan=protocol_plan,
        network_state=net,
        guardian=guardian_hint,
    )

    # Show everything together
    output = {
        "intent": intent.as_dict(),
        "network_state": net,
        "guardian_hint_present": guardian_hint is not None,
        "protocol_plan": protocol_plan,
        "route_decision": decision,
    }

    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
