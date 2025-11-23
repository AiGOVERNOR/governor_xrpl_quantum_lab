"""
ecosystem.cli.quantum_fusion_cli
--------------------------------

CLI for inspecting the Quantum Fusion Layer output.

Usage:
  python -m ecosystem.cli.quantum_fusion_cli
"""

import json

from ecosystem.pipeline_v5 import run_vqm_cycle_v5
from ecosystem.quantum_fusion import run_quantum_fusion


def main() -> None:
    # 1) pull a full pipeline snapshot
    state = run_vqm_cycle_v5()

    network_state = state.get("network_state", {})
    guardian_block = state.get("guardian")
    fee_horizon = state.get("fee_horizon", {})

    # Optional: extract a fee history if you have one
    fee_history = fee_horizon.get("history")  # you can adapt this later

    fusion = run_quantum_fusion(
        network_state=network_state,
        guardian_block=guardian_block,
        fee_history=fee_history,
        live_fee_hint=None,  # wire websockets here later if you like
    )

    print(json.dumps(fusion, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
