import json
import os
from dataclasses import dataclass
from typing import Optional

# This module loads the local Governor XRPL wallet from:
#   <repo_root>/config/governor_wallet.json
#
# It is intentionally tiny and dumb:
#   - No network calls
#   - No signing
#   - Just structured access to address/keys
#
# Live signing/submission can be layered on top later.

# Resolve: /data/data/.../governor_xrpl_quantum_lab/config/governor_wallet.json
_ECOSYSTEM_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.dirname(_ECOSYSTEM_DIR)
_WALLET_PATH = os.path.join(_REPO_ROOT, "config", "governor_wallet.json")


@dataclass
class GovernorWallet:
    address: str
    seed: Optional[str] = None
    privkey_hex: Optional[str] = None
    pubkey_hex: Optional[str] = None
    algorithm: Optional[str] = None
    created: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "address": self.address,
            "seed": self.seed,
            "privkey": self.privkey_hex,
            "pubkey": self.pubkey_hex,
            "algorithm": self.algorithm,
            "created": self.created,
        }


def load_governor_wallet(path: str | None = None) -> GovernorWallet:
    """
    Load the local Governor XRPL wallet.

    Expected JSON structure (config/governor_wallet.json):

    {
      "address": "...",
      "seed": "...",
      "privkey": "...",
      "pubkey": "...",
      "algorithm": "...",
      "created": "..."
    }
    """
    wallet_path = path or _WALLET_PATH

    if not os.path.exists(wallet_path):
        raise FileNotFoundError(
            f"Governor wallet not found at {wallet_path}. "
            "Generate it first with the local wallet generator script."
        )

    with open(wallet_path, "r") as f:
        data = json.load(f)

    address = data.get("address")
    if not address:
        raise ValueError(
            f"Wallet file {wallet_path} is missing 'address'. "
            "Delete it and regenerate a fresh wallet."
        )

    return GovernorWallet(
        address=address,
        seed=data.get("seed"),
        privkey_hex=data.get("privkey"),
        pubkey_hex=data.get("pubkey"),
        algorithm=data.get("algorithm"),
        created=data.get("created"),
    )


def debug_print_wallet(path: str | None = None) -> None:
    """
    Convenience helper to quickly inspect the wallet from the CLI.
    """
    wallet = load_governor_wallet(path)
    print("=== Governor Wallet (Local) ===")
    print(f"Address  : {wallet.address}")
    print(f"Algorithm: {wallet.algorithm}")
    print(f"Created  : {wallet.created}")
