"""
ecosystem.cli.sdk_demo_cli
--------------------------
Tiny CLI to demo the VQM SDK client.

Usage:

    python -m ecosystem.cli.sdk_demo_cli

This will:

  - Call the VQM pipeline
  - Build a simple payment intent (1 XRP)
  - Ask the Flow Engine v2 for a plan
  - Print the decision as JSON
"""

import json

from ecosystem.sdk import VQMSDKClient


def main() -> None:
    client = VQMSDKClient()

    decision = client.simple_payment(
        source_account="rSOURCE_ACCOUNT_PLACEHOLDER",
        destination_account="rDESTINATION_ACCOUNT_PLACEHOLDER",
        amount_drops=1_000_000,  # 1 XRP in drops
        memo="sdk_demo",
    )

    print(json.dumps(decision, indent=2, sort_keys=True))
    print("\n--- Summary ---")
    print(client.explain(decision))


if __name__ == "__main__":
    main()
