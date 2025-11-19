import json
import os
from typing import Any, Dict, List

# Where we persist high-level network snapshots.
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
MEMORY_FILE_PATH = os.path.abspath(os.path.join(DATA_DIR, "vqm_memory.jsonl"))


def _ensure_data_dir() -> None:
    os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)


def append_state(snapshot: Dict[str, Any]) -> None:
    """
    Append a single snapshot (typically containing timestamp + network_state)
    as one JSON line on disk.
    """
    _ensure_data_dir()
    try:
        with open(MEMORY_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, separators=(",", ":")) + "\n")
    except Exception:
        # Memory is non-critical: never crash the pipeline because of IO issues.
        pass


def load_recent_states(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Load up to `limit` most recent memory snapshots from disk.

    If the memory file does not exist or is unreadable, we gracefully
    return an empty list.
    """
    if not os.path.exists(MEMORY_FILE_PATH):
        return []

    try:
        with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    if not lines:
        return []

    tail = lines[-limit:]
    out: List[Dict[str, Any]] = []
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
