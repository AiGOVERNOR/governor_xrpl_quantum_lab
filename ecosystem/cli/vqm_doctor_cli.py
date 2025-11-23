# ecosystem/cli/vqm_doctor_cli.py

"""
VQM Doctor CLI
--------------

Run:

  python -m ecosystem.cli.vqm_doctor_cli

and you’ll get a JSON blob showing which subsystems are healthy / broken.
"""

import json
from ecosystem.vqm_doctor import run_all_checks


def main() -> None:
    report = run_all_checks()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
