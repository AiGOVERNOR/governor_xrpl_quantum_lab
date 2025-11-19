"""
AIVQM Integrators SDK Layer

Thin, read-only client for talking to a running VQM API node.

Usage:

    from ecosystem.sdk import VQMClient

    client = VQMClient()  # default: http://127.0.0.1:8000
    state = client.get_full_state()
    print(state["network_state"])
"""

from .client import VQMClient, VQMClientError  # noqa: F401
