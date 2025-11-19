from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import os


def _data_dir() -> Path:
    # repo_root / "data"
    here = Path(__file__).resolve()
    ecosystem_dir = here.parent.parent
    repo_root = ecosystem_dir.parent
    data = repo_root / "data"
    data.mkdir(exist_ok=True, parents=True)
    return data


def append_ledger_entry(entry: Dict[str, Any]) -> str:
    """
    Append a single structural ledger entry to data/vqm_infra_ledger.jsonl.

    This is local-only telemetry for your own infra intelligence.
    """
    data_dir = _data_dir()
    path = data_dir / "vqm_infra_ledger.jsonl"

    try:
        with path.open("a", encoding="utf-8") as f:
            json.dump(entry, f)
            f.write("\n")
    except Exception:
        # Never break the main pipeline because of logging.
        pass

    return str(path)
