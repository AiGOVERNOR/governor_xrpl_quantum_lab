from __future__ import annotations

import json
import os
from typing import Tuple, Dict, Any

from .models import FeePolicy, AccountRoles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "governor_hooks_config.json")


def _ensure_config_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _default_config() -> Dict[str, Any]:
    """
    Safe default config.

    You can edit config/governor_hooks_config.json later
    to point to different infra accounts or adjust fees.
    """
    return {
        "version": "1.0",
        "fee_policy": {
            "bps": 5,
            "min_drops": 10,
            "max_bps": 50,
        },
        "accounts": {
            # These SHOULD be edited to your actual accounts.
            # For now they are placeholders; aetherborn_swarm can override.
            "source": "rEXAMPLE_SOURCE_ACCOUNT",
            "vault": "rEXAMPLE_VAULT_ACCOUNT",
            "fee_pool": "rEXAMPLE_FEE_POOL_ACCOUNT",
        },
        "features": {
            "iso20022_logging": True,
            "enforce_min_reserve": True,
        },
    }


def _write_default_config_if_missing(path: str) -> None:
    if not os.path.exists(path):
        _ensure_config_dir()
        cfg = _default_config()
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        print(f"[HookSuite] Wrote default config to {path}")


def load_hooks_config(path: str = DEFAULT_CONFIG_PATH) -> Tuple[FeePolicy, AccountRoles, Dict[str, Any]]:
    """
    Load fee policy + account roles + raw config dict.

    If file does not exist, a default is created first.
    """
    _write_default_config_if_missing(path)

    with open(path) as f:
        raw = json.load(f)

    fee_policy = FeePolicy.from_dict(raw.get("fee_policy", {}))
    accounts = AccountRoles.from_dict(raw["accounts"])
    features = raw.get("features", {})

    return fee_policy, accounts, features
