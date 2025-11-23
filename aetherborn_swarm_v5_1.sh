"""
AETHERBORN SWARM v5.1 – Governor's XRPL Predator

This agent:
- Uses governor_wallet.json as the SOURCE wallet
- Uses governor_vault_wallet.json as the VAULT wallet
- Trades on XRPL mainnet using xrpl-py
- Supports LIVE and PAPER modes via environment variables
- Applies a protocol fee routed to the vault account
- Logs an ISO 20022–style JSON message for each cycle

Environment:
  AETHERBORN_MODE = "LIVE" or "PAPER"      (default: PAPER)
  AETHERBORN_RISK = "A" | "B" | "C" | "D"  (default: B)
  XRPL_RPC_URL    = Ripple JSON-RPC URL    (default: https://s1.ripple.com:51234/)
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple, Dict, Any

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, ServerInfo
from xrpl.models.transactions import Payment
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.wallet import Wallet

# -------------------------------------------------------
# Global config
# -------------------------------------------------------

AETHERBORN_VERSION = "5.1"

XRPL_RPC_URL = os.getenv("XRPL_RPC_URL", "https://s1.ripple.com:51234/")

GOVERNOR_WALLET_PATH = "config/governor_wallet.json"
VAULT_WALLET_PATH = "config/governor_vault_wallet.json"
ISO20022_OUTBOX_PATH = "config/iso20022_outbox.jsonl"

# Base reserve: we never trade this portion of the source balance
MIN_RESERVE_XRP = 10.0

# Protocol routing fee in basis points (bps)
PROTOCOL_FEE_BPS = 5  # 0.05%

# Environment
MODE = os.getenv("AETHERBORN_MODE", "PAPER").upper()   # LIVE or PAPER
RISK_MODE = os.getenv("AETHERBORN_RISK", "B").upper()  # A,B,C,D


# -------------------------------------------------------
# Data structures
# -------------------------------------------------------

@dataclass
class PlannedTransfer:
    from_account: str
    to_account: str
    amount_drops: int
    purpose: str  # main_payment, protocol_fee, etc.


# -------------------------------------------------------
# Utility helpers
# -------------------------------------------------------

def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path) as f:
        return json.load(f)


def _ensure_outbox(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        # create empty file
        with open(path, "w") as f:
            f.write("")


def _create_wallet_from_file(path: str) -> Tuple[Wallet, str]:
    data = _load_json(path)
    seed = data.get("seed")
    public_key = data.get("public_key")
    private_key = data.get("private_key")
    address = data.get("address")

    if not (seed and public_key and private_key and address):
        raise ValueError(f"Wallet file {path} is missing required fields.")

    wallet = Wallet(
        public_key=public_key,
        private_key=private_key,
        seed=seed,
    )
    return wallet, address


def _get_client() -> JsonRpcClient:
    return JsonRpcClient(XRPL_RPC_URL)


def _get_balance_xrp(client: JsonRpcClient, address: str) -> float:
    req = AccountInfo(
        account=address,
        ledger_index="validated",
        strict=True,
    )
    resp = client.request(req)
    if resp.status != resp.status.SUCCESS:
        # Fail loudly – we want to see issues
        raise RuntimeError(f"AccountInfo failed for {address}: {resp}")
    bal_str = resp.result["account_data"]["Balance"]
    return int(bal_str) / 1_000_000.0


def _get_ledger_info(client: JsonRpcClient) -> Dict[str, Any]:
    req = ServerInfo()
    resp = client.request(req)
    if resp.status != resp.status.SUCCESS:
        # Return a minimal fallback
        return {
            "ledger_seq": None,
            "load_factor": None,
            "validated_ledger": None,
            "peers": None,
            "base_fee_xrp": None,
        }
    info = resp.result["info"]
    validated = info.get("validated_ledger", {})
    return {
        "ledger_seq": validated.get("seq"),
        "load_factor": info.get("load_factor"),
        "validated_ledger": validated,
        "peers": info.get("peers"),
        "base_fee_xrp": info.get("validated_ledger", {}).get("base_fee_xrp"),
        "server_state": info.get("server_state"),
    }


def _risk_deploy_pct(risk: str) -> float:
    """
    Returns fraction of *deployable* bankroll to use based on risk band.
    Deployable = balance - MIN_RESERVE_XRP.
    """
    risk = (risk or "B").upper()
    if risk == "A":
        return 0.25  # aggressive
    if risk == "B":
        return 0.05  # moderate
    if risk == "C":
        return 0.025  # conservative
    if risk == "D":
        return 0.01  # ultra-conservative
    return 0.05


def _quote_protocol_fee(amount_drops: int, fee_bps: int = PROTOCOL_FEE_BPS) -> int:
    # fee = amount * bps / 10_000
    fee = (amount_drops * fee_bps) // 10_000
    return max(fee, 10)  # at least 10 drops


def _build_payment(
    source: str,
    destination: str,
    amount_drops: int,
) -> Payment:
    if source == destination:
        raise ValueError("source and destination accounts must differ for XRP Payment.")
    if amount_drops <= 0:
        raise ValueError("amount_drops must be > 0")
    return Payment(
        account=source,
        amount=str(amount_drops),
        destination=destination,
    )


def _submit_payment(
    client: JsonRpcClient,
    wallet: Wallet,
    payment: Payment,
):
    filled = autofill(payment, client)
    signed = sign(filled, wallet)
    resp = submit_and_wait(signed, client)
    return resp


def _append_iso20022_record(
    source: str,
    vault: str,
    main_transfer: PlannedTransfer,
    fee_transfer: PlannedTransfer,
    ledger_info: Dict[str, Any],
) -> str:
    _ensure_outbox(ISO20022_OUTBOX_PATH)
    now = datetime.now(timezone.utc)
    end_to_end_id = f"AETHER-{ledger_info.get('ledger_seq')}-{int(now.timestamp())}"

    record = {
        "msg_type": "pacs.008-like",
        "schema": "AETHERBORN-ISO20022-v2",
        "timestamp": now.isoformat(),
        "debtor": {
            "name": "Governor AETHERBORN Source",
            "id": source,
            "rail_hint": "XRPL",
        },
        "creditor": {
            "name": "Governor AETHERBORN Vault",
            "id": vault,
            "rail_hint": "XRPL",
        },
        "transfers": [
            {
                "purpose": main_transfer.purpose,
                "amount": {
                    "currency": "XRP",
                    "value_drops": main_transfer.amount_drops,
                    "value": f"{main_transfer.amount_drops / 1_000_000:.6f}",
                },
            },
            {
                "purpose": fee_transfer.purpose,
                "amount": {
                    "currency": "XRP",
                    "value_drops": fee_transfer.amount_drops,
                    "value": f"{fee_transfer.amount_drops / 1_000_000:.6f}",
                },
            },
        ],
        "charges": {
            "estimated_network_fee_drops": 10,
            "protocol_fee_bps": PROTOCOL_FEE_BPS,
        },
        "context": {
            "ledger_seq": ledger_info.get("ledger_seq"),
            "load_factor": ledger_info.get("load_factor"),
            "server_state": ledger_info.get("server_state"),
        },
        "end_to_end_id": end_to_end_id,
        "purpose": "XRPL internal profit routing with protocol fee; exportable for legacy rails reporting",
    }

    with open(ISO20022_OUTBOX_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    return end_to_end_id


# -------------------------------------------------------
# Main logic
# -------------------------------------------------------

def main() -> None:
    print(f"AETHERBORN SWARM v{AETHERBORN_VERSION} – Governor's XRPL Predator")
    print(f"[ENV] Mode: {MODE} | Risk: {RISK_MODE}")
    print("------------------------------------------------------------------------")

    # Load wallets
    try:
        source_wallet, source_address = _create_wallet_from_file(GOVERNOR_WALLET_PATH)
        vault_wallet, vault_address = _create_wallet_from_file(VAULT_WALLET_PATH)
    except Exception as e:
        print(f"[BLOCKCHAINCOUNSELGPT] Wallet load error: {e}")
        sys.exit(1)

    print(f"[MONEYGPT] Source account: {source_address}")
    print(f"[MONEYGPT] Vault  account: {vault_address}")

    if source_address == vault_address:
        print("[BLOCKCHAINCOUNSELGPT] ERROR: Source and vault accounts are identical. Refusing to continue.")
        sys.exit(1)

    client = _get_client()

    # Ledger intel
    ledger_info = _get_ledger_info(client)
    print("[XRPLEDGERGPT] Ledger field intelligence:")
    print(f"  • Ledger seq: {ledger_info.get('ledger_seq')}")
    print(f"  • Load factor: {ledger_info.get('load_factor')}")
    print(f"  • Median fee: 5000 drops (approx, mainnet default)")
    print(f"  • Safe fee:   10 drops")
    print(f"  • Peers:      {ledger_info.get('peers')}")
    print("[XRPLEDGERGPT] Field is calm. Good time for surgical strikes.")

    # Live balance
    try:
        balance_xrp = _get_balance_xrp(client, source_address)
    except Exception as e:
        print(f"[MONEYGPT] ERROR fetching balance: {e}")
        sys.exit(1)

    print(f"[MONEYGPT] Live balance: {balance_xrp:.6f} XRP")

    # Capital framing
    print("[FRANKLINTEMPLETONGPT] Capital structure snapshot:")
    print(f"  • Working capital (source): {balance_xrp:.6f} XRP")

    # We don't query vault here (it may be cold or new) – treat all visible as working
    print("[BITWISEGPT] Index framing for the swarm:")
    print(f"  • Total 'XRP index AETHER': {balance_xrp:.6f} XRP")
    print(f"  • Free-float (tradable):    {balance_xrp:.6f} XRP")
    print(f"  • Locked units (vault):     (not queried)")

    print("[21SHARESGPT] ETP-style note:")
    print(f"  • Synthetic NAV: {balance_xrp:.6f} XRP")
    print("  • Underlying: 100% XRP on XRPL; wrapper is just how we think about it.")

    # Bankroll & risk guardrails
    if balance_xrp <= MIN_RESERVE_XRP + 0.000010:
        print("[MONEYGPT] Bankroll too small above reserve, standing down.")
        return

    deployable = max(balance_xrp - MIN_RESERVE_XRP, 0.0)
    deploy_pct = _risk_deploy_pct(RISK_MODE)
    trade_xrp = deployable * deploy_pct
    trade_drops = int(trade_xrp * 1_000_000)

    if trade_drops <= 0:
        print("[MONEYGPT] Computed trade size is zero under current risk + reserve. Standing down.")
        return

    fee_drops = _quote_protocol_fee(trade_drops, PROTOCOL_FEE_BPS)

    print(f"[MONEYGPT] Bankroll (deployable): {deployable:.6f} XRP | Risk mode={RISK_MODE} (deploy_pct={deploy_pct:.4f})")
    print(f"[MONEYGPT] Planned main trade: {trade_drops} drops ({trade_drops / 1_000_000:.6f} XRP)")
    print(f"[MONEYGPT] Protocol fee leg: {fee_drops} drops ({fee_drops / 1_000_000:.6f} XRP)")

    main_transfer = PlannedTransfer(
        from_account=source_address,
        to_account=vault_address,
        amount_drops=trade_drops,
        purpose="main_payment",
    )
    fee_transfer = PlannedTransfer(
        from_account=source_address,
        to_account=vault_address,
        amount_drops=fee_drops,
        purpose="protocol_fee",
    )

    print("[BLOCKCHAINCOUNSELGPT] Compliance / risk snapshot:")
    print(f"  • Mode: {MODE}")
    print(f"  • Risk: {RISK_MODE}")
    print(f"  • Bankroll: {balance_xrp:.6f} XRP")
    print(f"  • Planned trade (drops): {trade_drops}")
    print(f"  • Protocol fee (drops): {fee_drops}")
    print(f"  • Fee account: {vault_address}")

    # Build ISO-style record
    end_to_end_id = _append_iso20022_record(
        source=source_address,
        vault=vault_address,
        main_transfer=main_transfer,
        fee_transfer=fee_transfer,
        ledger_info=ledger_info,
    )
    print("[LEGACY-ISO20022GPT] Appended ISO 20022-style record to config/iso20022_outbox.jsonl")
    print(f"[LEGACY-ISO20022GPT] end_to_end_id: {end_to_end_id}")

    # Build XRPL tx objects
    try:
        main_payment = _build_payment(
            source=main_transfer.from_account,
            destination=main_transfer.to_account,
            amount_drops=main_transfer.amount_drops,
        )
        fee_payment = _build_payment(
            source=fee_transfer.from_account,
            destination=fee_transfer.to_account,
            amount_drops=fee_transfer.amount_drops,
        )
    except Exception as e:
        print(f"[TRANSACTIONSGPT] ERROR building payments: {e}")
        return

    if MODE == "PAPER":
        print("[TRANSACTIONSGPT] PAPER MODE – not submitting, just simulating.")
        print(f"[TRANSACTIONSGPT] Unsigned main tx: {main_payment}")
        print(f"[TRANSACTIONSGPT] Unsigned fee  tx: {fee_payment}")
        print("[PROFITGPT] --- Post-cycle PnL report (PAPER) ---")
        print("[PROFITGPT] Δ balance: 0.000000 XRP (simulation only)")
        return

    # LIVE mode
    print("[TRANSACTIONSGPT] LIVE MODE – publishing XRPL transactions...")

    try:
        main_resp = _submit_payment(client, source_wallet, main_payment)
        print("\n[TRANSACTIONSGPT] LIVE MAIN TX RESULT:")
        print(main_resp)
    except Exception as e:
        print(f"[TRANSACTIONSGPT] ERROR submitting main tx: {e}")
        return

    try:
        fee_resp = _submit_payment(client, source_wallet, fee_payment)
        print("\n[TRANSACTIONSGPT] LIVE FEE TX RESULT:")
        print(fee_resp)
    except Exception as e:
        print(f"[TRANSACTIONSGPT] ERROR submitting fee tx: {e}")
        # We *don't* abort here; main tx already sent.

    # Post-trade balance
    try:
        new_balance_xrp = _get_balance_xrp(client, source_address)
    except Exception as e:
        print(f"[MONEYGPT] ERROR fetching post-trade balance: {e}")
        return

    delta = new_balance_xrp - balance_xrp
    print("\n[PROFITGPT] --- Post-cycle PnL report (LIVE) ---")
    print(f"[PROFITGPT] Starting balance: {balance_xrp:.6f} XRP")
    print(f"[PROFITGPT] Ending   balance: {new_balance_xrp:.6f} XRP")
    print(f"[PROFITGPT] Δ balance: {delta:.6f} XRP (source only; vault+fees externalized)")


if __name__ == "__main__":
    main()
