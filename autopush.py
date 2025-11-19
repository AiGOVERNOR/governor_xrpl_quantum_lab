# autopush.py
import subprocess
import time
from ecosystem.orchestrator import run_vqm_cycle


def autopush_vqm(interval_minutes: int = 15):
    """
    Governor's autonomous VQM autopush engine.
    Runs a full VQM cycle, commits the state, and pushes it to GitHub.
    """
    while True:
        state = run_vqm_cycle()

        ledg = state["network_state"]["ledger_seq"]
        msg = f"Auto VQM commit — Ledger {ledg}"

        subprocess.run(["git", "add", "-A"])
        subprocess.run(["git", "commit", "-m", msg])
        subprocess.run(["git", "push", "origin", "main"])

        print(f"[Autopush] {msg}")
        time.sleep(interval_minutes * 60)
