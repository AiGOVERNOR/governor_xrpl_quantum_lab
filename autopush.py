import subprocess
import time
from datetime import datetime
from ecosystem.orchestrator import run_vqm_cycle


def git(*cmd):
    """Run a git command and return output."""
    return subprocess.run(["git", *cmd], capture_output=True, text=True)


def autopush_vqm(interval_minutes=10):
    """Autopush cycle for VQM ecosystem updates."""
    while True:
        try:
            # Generate live XRPL state
            state = run_vqm_cycle()

            ledger = state["network_state"]["ledger_seq"]
            msg = f"auto-vqm-ledger-{ledger}"

            # Stage changes
            git("add", "-A")

            # Commit (ignore if nothing changed)
            git("commit", "-m", msg)

            # Push to GitHub (SSH)
            push = git("push", "origin", "main")

            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            print(f"[{now}] Commit {msg}")
            print(push.stdout or push.stderr)

        except Exception as e:
            print("[ERROR]", e)

        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    autopush_vqm()
