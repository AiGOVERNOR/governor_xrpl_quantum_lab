"""
VQM Memory Engine

Lightweight, append-only memory store for XRPL network_state snapshots.
Backed by a JSONL file on disk so the VQM ecosystem can build temporal
context across runs.

This module is intentionally simple and dependency-free.
"""

from .store import (
    MEMORY_FILE_PATH,
    append_state,
    load_recent_states,
)

__all__ = [
    "MEMORY_FILE_PATH",
    "append_state",
    "load_recent_states",
]
