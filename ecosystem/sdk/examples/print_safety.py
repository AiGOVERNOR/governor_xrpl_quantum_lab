"""
Example: read-only safety check via VQM Integrators SDK.

Usage:

  # Local (in-process) mode:
  python -m ecosystem.sdk.examples.print_safety

  # HTTP mode (if api_vqm is running at http://127.0.0.1:8000):
  VQM_MODE=http VQM_BASE_URL=http://127.0.0.1:8000 \
    python -m ecosystem.sdk.examples.print_safety
"""

import json
import os

from ecosystem.sdk.client import VQMClient
from ecosystem.sdk.models import VQMClientConfig


def main() -> None:
    mode = os.environ.get("VQM_MODE", "local").lower()
    base_url = os.environ.get("VQM_BASE_URL")

    if mode == "http":
        config = VQMClientConfig(mode="http", base_url=base_url)
    else:
        config = VQMClientConfig(mode="local")

    client = VQMClient(config=config)
    safety = client.get_safety_summary()

    print(json.dumps(safety, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
