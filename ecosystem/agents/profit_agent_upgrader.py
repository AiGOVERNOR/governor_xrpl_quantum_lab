# ecosystem/agents/profit_agent_upgrader.py

import subprocess
from pathlib import Path
from typing import Any, Dict


def _repo_root() -> Path:
    # agents/ -> ecosystem/ -> repo_root
    return Path(__file__).resolve().parents[2]


def upgrade_repo() -> Dict[str, Any]:
    """
    Attempt a safe `git pull` on the repo.
    Does NOT restart processes, just fetches code.
    """
    root = _repo_root()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "pull"],
            capture_output=True,
            text=True,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "changed": proc.returncode == 0,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "changed": False, "error": repr(exc)}


def safe_auto_upgrade(enabled: bool) -> Dict[str, Any]:
    """
    Wrapper used by the runner. If disabled, it's a no-op.
    """
    if not enabled:
        return {"ok": True, "changed": False, "skipped": True}
    return upgrade_repo()
