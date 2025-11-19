"""
Integrator demo for the VQM SDK.

Usage:

    python -m ecosystem.cli.integrator_demo
"""

import json

from ecosystem.sdk import VQMClient, VQMClientError


def main() -> None:
    client = VQMClient()  # default: http://127.0.0.1:8000

    try:
        state = client.get_full_state()
    except VQMClientError as exc:
        print(f"[VQM SDK] Error: {exc}")
        return

    print("=== VQM Network State ===")
    print(
        json.dumps(
            {
                "ledger_seq": state.network_state.ledger_seq,
                "txn_base_fee": state.network_state.txn_base_fee,
                "txn_median_fee": state.network_state.txn_median_fee,
                "recommended_fee_drops": state.network_state.recommended_fee_drops,
                "load_factor": state.network_state.load_factor,
            },
            indent=2,
        )
    )

    if state.guardian:
        print("\n=== Guardian Snapshot ===")
        print(
            json.dumps(
                {
                    "mode": state.guardian.mode,
                    "policy_status": state.guardian.policy_status,
                    "explanation": state.guardian.explanation,
                },
                indent=2,
            )
        )

    if state.fee_horizon:
        print("\n=== Fee Horizon ===")
        print(
            json.dumps(
                {
                    "band": state.fee_horizon.band,
                    "horizon_seconds": state.fee_horizon.horizon_seconds,
                    "trend_short": state.fee_horizon.trend_short,
                    "trend_long": state.fee_horizon.trend_long,
                },
                indent=2,
            )
        )

    if state.mesh_intent:
        print("\n=== Mesh Intent ===")
        print(
            json.dumps(
                {
                    "mode": state.mesh_intent.mode,
                    "priority": state.mesh_intent.priority,
                    "band": state.mesh_intent.band,
                },
                indent=2,
            )
        )

    print("\n=== Tools ===")
    print(json.dumps(state.tools, indent=2))


if __name__ == "__main__":
    main()
