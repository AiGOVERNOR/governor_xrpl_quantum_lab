import json
import os

def load_agent_config(name: str) -> dict:
    """
    Loads agent config as a plain Python dict.
    Compatible with all runners.
    """
    base = os.path.dirname(__file__)
    path = os.path.join(base, f"{name}.json")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Agent config not found: {path}")

    with open(path, "r") as f:
        return json.load(f)
