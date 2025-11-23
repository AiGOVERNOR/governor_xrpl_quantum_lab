"""
ecosystem.cli.protocol_graph_cli
--------------------------------
CLI helper to inspect the Protocol Graph Layer.

Usage:
  python -m ecosystem.cli.protocol_graph_cli
"""


import json

from ecosystem.tx.graph import protocol_graph


def main() -> None:
    data = {
        "protocols": protocol_graph.list_protocols(),
        "transitions": protocol_graph.list_transitions(),
        "sample_simple_payment": protocol_graph.advise_for_intent(
            intent_kind="simple_payment",
            band="extreme",
            guardian_mode="fee_pressure",
            risk_budget=3,
        ),
        "sample_salary_stream": protocol_graph.advise_for_intent(
            intent_kind="salary_stream",
            band="normal",
            guardian_mode="normal",
            risk_budget=3,
        ),
        "sample_escrow": protocol_graph.advise_for_intent(
            intent_kind="escrow_milestone",
            band="elevated",
            guardian_mode="fee_pressure",
            risk_budget=4,
        ),
    }
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
