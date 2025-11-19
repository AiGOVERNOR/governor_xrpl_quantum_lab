import os
import time
import subprocess
from datetime import datetime

REPO_PATH = os.path.dirname(os.path.abspath(__file__))
POLL_INTERVAL = 10  # seconds


def run(cmd):
    """Run a shell command and capture output/errors."""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=REPO_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def git_changed():
    """Check if there are uncommitted changes."""
    out, _ = run("git status --porcelain")
    return len(out.strip()) > 0


def git_autopush():
    """Stage, commit, push to origin/main."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print(f"[ AUTO-PUSH ] Detected changes → committing @ {timestamp}")

    run("git add -A")
    run(f'git commit -m "MeshPulse @ {timestamp}"')

    out, err = run("git push origin main")

    if err:
        print("[ ERROR pushing ]", err)
    else:
        print("[ PUSHED ]", out)


def main():
    print("=== Governor XRPL VQM AutoPush Engine Online ===")
    print(f"Monitoring: {REPO_PATH}")

    while True:
        if git_changed():
            git_autopush()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
