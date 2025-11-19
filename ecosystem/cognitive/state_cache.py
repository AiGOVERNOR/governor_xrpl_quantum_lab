from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


HISTORY_PATH = Path("data/vqm_cognitive_history.jsonl")


def _ensure_history_dir() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def append_snapshot(snapshot: Dict[str, Any]) -> None:
    """
    Append a single snapshot to the JSONL history file.

    This is intentionally small and append-only so it plays nice
    with Termux and low-resource environments.
    """
    _ensure_history_dir()
    line = json.dumps(snapshot, separators=(",", ":"))
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_history(max_items: int = 256) -> List[Dict[str, Any]]:
    """
    Load up to the last `max_items` snapshots from disk.
    Returns newest-last list.
    """
    if not HISTORY_PATH.exists():
        return []

    lines: List[str] = []
    with HISTORY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)

    lines = lines[-max_items:]
    history: List[Dict[str, Any]] = []
    for line in lines:
        try:
            history.append(json.loads(line))
        except Exception:
            # ignore corrupted lines
            continue
    return history


def append_and_load(snapshot: Dict[str, Any], max_items: int = 256) -> List[Dict[str, Any]]:
    """
    Append a snapshot, then return fresh history.
    """
    append_snapshot(snapshot)
    return load_history(max_items=max_items)
