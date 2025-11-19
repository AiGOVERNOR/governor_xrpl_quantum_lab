from typing import Any, Dict, List


_SECRET_KEYS: List[str] = [
    "seed",
    "secret",
    "mnemonic",
    "family_seed",
    "tx_blob",
    "signed_tx",
    "wallet_key",
]


def sanitize_proposal(proposal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove any fields that look like secrets or signed blobs.

    This is defensive: we do not expect the mesh to ever
    generate these fields, but if something upstream misbehaves,
    we strip them here.
    """
    cleaned: Dict[str, Any] = {}

    for k, v in proposal.items():
        if k.lower() in _SECRET_KEYS:
            # Drop silently; you can log if you add logging later
            continue
        cleaned[k] = v

    return cleaned


def validate_safe(proposal: Dict[str, Any]) -> bool:
    """
    Basic safety check: ensure no obviously sensitive keys remain.
    """
    keys = {k.lower() for k in proposal.keys()}
    return keys.isdisjoint(_SECRET_KEYS)
