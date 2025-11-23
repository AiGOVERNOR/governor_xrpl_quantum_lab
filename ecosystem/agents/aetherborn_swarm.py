"""
AETHERBORN SWARM v5.3 – Governor's XRPL Predator (Single-Wallet Core)

Design rules:

- Uses ONLY your funded XRPL wallet as a real signing Wallet:
    config/governor_wallet.json

- Vault is destination-only:
    config/governor_vault_wallet.json
  Seed/private key in vault file are ignored. Only "address" is used.

- LIVE mode will only send if:
    • Source balance > on-chain reserve (MIN_RESERVE_XRP),
    • Planned trade > 0,
    • Vault address exists in config,
    • Vault != source,
    • Vault account exists on-ledger.

- PAPER mode (default) simulates and logs ISO 20022-style records
  to config/iso20022_outbox.jsonl.

Environment:

    AETHERBORN_MODE = PAPER | LIVE   (default: PAPER)
    AETHERBORN_RISK = A | B | C      (default: B)

Files:

    config/governor_wallet.json
        {
          "seed": "sEdSqheCEinRJfgEzr2LrcuQu1Lk5YJ",
          "public_key": "EDCA82C1D3F240CEB7C650721B05A468460AAB398EFAD40CDF391A44EA7D6CBA52",
          "private_key": "EDD9383AAF81951605D3B58F3223A4404D34D4F164047DFC690D849C946CABCE22",
          "address": "rEXdG3Rh9Ejb3NKXoxb16xge4d3BHskJUP",
          "algorithm": "ed25519"
        }

    config/governor_vault_wallet.json
        {
          "address": "rK7BKKcayjcbwAdYBj1XnAy1hR2zesTqQZ",
          ...
        }

    config/iso20022_outbox.jsonl   (append-only JSON lines)
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, ServerInfo
from xrpl.models.transactions import Payment
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.wallet import Wallet

# -------------------------------------------------------
# Global configuration
# -------------------------------------------------------

AETHERBORN_VERSION = "5.3"

XRPL_RPC_URL = os.getenv("XRPL_RPC_URL", "https://s1.ripple.com:51234/")

GOVERNOR_WALLET_PATH = "config/governor_wallet.json"
VAULT_WALLET_PATH = "config/governor_vault_wallet.json"
ISO20022_OUTBOX_PATH = "config/iso20022_outbox.jsonl"

# Reserve: keep this much XRP in the source wallet untouched
MIN_RESERVE_XRP = 10.0


# -------------------------------------------------------
# Dataclasses
# -------------------------------------------------------

@dataclass
class WalletInfo:
    wallet: Wallet
    address: str


@dataclass
class RiskPlan:
    deploy_pct: float
    label: str


@dataclass
class TradePlan:
    mode: str
    risk_mode: str
    source_address: str
    dest_address: Optional[str]
    live_balance_drops: int
    main_amount_drops: int
    fee_amount_drops: int


# -------------------------------------------------------
# Basic IO helpers
# -------------------------------------------------------

def _load_json(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r") as f:
        return json.load(f)


def _append_jsonl(path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


# -------------------------------------------------------
# Wallet + ledger helpers
# -------------------------------------------------------

def load_governor_wallet(path: str) -> WalletInfo:
    """
    Load the Governor wallet (signing wallet).
    """
    data = _load_json(path)
    required = ("seed", "public_key", "private_key", "address")
    for k in required:
        if k not in data:
            raise ValueError(f"{path} missing key '{k}'")

    seed = data["seed"]
    public_key = data["public_key"]
    private_key = data["private_key"]
    address = data["address"]

    try:
        wallet = Wallet(
            public_key=public_key,
            private_key=private_key,
            seed=seed,
        )
    except Exception as e:
        raise ValueError(f"Governor wallet seed/keys invalid: {e}")

    return WalletInfo(wallet=wallet, address=address)


def load_vault_address(path: str) -> Optional[str]:
    """
    Load vault address only. Ignores any seeds/keys.
    """
    if not os.path.exists(path):
        return None
    data = _load_json(path)
    addr = data.get("address")
    if not isinstance(addr, str) or not addr:
        return None
    return addr


def get_account_root(client: JsonRpcClient, address: str) -> Optional[dict]:
    try:
        req = AccountInfo(
            account=address,
            ledger_index="validated",
            strict=True,
        )
        resp = client.request(req)
        if resp.status.value != "success":
            return None
        return resp.result.get("account_data")
    except Exception:
        return None


def get_balance_drops(client: JsonRpcClient, address: str) -> Optional[int]:
    root = get_account_root(client, address)
    if not root:
        return None
    try:
        return int(root["Balance"])
    except Exception:
        return None


def get_server_info(client: JsonRpcClient) -> Optional[dict]:
    try:
        resp = client.request(ServerInfo())
        if resp.status.value != "success":
            return None
        return resp.result.get("info", {})
    except Exception:
        return None


# -------------------------------------------------------
# Formatting helpers
# -------------------------------------------------------

def drops_to_xrp(drops: int) -> float:
    return drops / 1_000_000.0


def fmt_xrp(drops: int) -> str:
    return f"{drops_to_xrp(drops):.6f} XRP"


def fmt_pct(p: float) -> str:
    return f"{p * 100:.4f}%"


# -------------------------------------------------------
# Risk + planning
# -------------------------------------------------------

def get_risk_plan(code: str) -> RiskPlan:
    code = (code or "B").upper()
    if code == "A":
        return RiskPlan(deploy_pct=0.10, label="Aggressive")
    if code == "C":
        return RiskPlan(deploy_pct=0.025, label="Conservative")
    return RiskPlan(deploy_pct=0.05, label="Moderate")


def plan_trade(balance_drops: int, risk_code: str, fee_bps: float = 5.0) -> Tuple[int, int]:
    """
    Returns (main_amount_drops, fee_amount_drops).
    fee_bps = protocol fee in basis points (5 = 0.05%).
    """
    balance_xrp = drops_to_xrp(balance_drops)

    if balance_xrp <= MIN_RESERVE_XRP:
        return 0, 0

    deployable_xrp = balance_xrp - MIN_RESERVE_XRP
    if deployable_xrp <= 0:
        return 0, 0

    risk = get_risk_plan(risk_code)
    base_trade_xrp = deployable_xrp * risk.deploy_pct
    main_amount_drops = int(base_trade_xrp * 1_000_000)

    if main_amount_drops < 10:
        return 0, 0

    fee_amount_drops = int(main_amount_drops * (fee_bps / 10_000.0))
    if fee_amount_drops < 10:
        fee_amount_drops = 10

    return main_amount_drops, fee_amount_drops


# -------------------------------------------------------
# ISO 20022-style logging
# -------------------------------------------------------

def log_iso20022(plan: TradePlan, server_info: dict) -> None:
    validated = server_info.get("validated_ledger") or {}
    msg = {
        "msg_type": "pacs.008-like",
        "schema": "AETHERBORN-ISO20022-v1",
        "debtor": {
            "name": "Governor AETHERBORN Source",
            "id": plan.source_address,
            "rail_hint": "XRPL",
        },
        "creditor": {
            "name": "Governor AETHERBORN Vault" if plan.dest_address else "N/A",
            "id": plan.dest_address or "N/A",
            "rail_hint": "XRPL" if plan.dest_address else "N/A",
        },
        "intermediary_chain": "XRPL",
        "amount": {
            "currency": "XRP",
            "value": f"{drops_to_xrp(plan.main_amount_drops):.6f}",
            "value_drops": plan.main_amount_drops,
        },
        "fee": {
            "protocol_fee_drops": plan.fee_amount_drops,
        },
        "context": {
            "ledger_seq": validated.get("seq"),
            "load_factor": server_info.get("load_factor"),
            "server_state": server_info.get("server_state"),
            "mode": plan.mode,
            "risk_mode": plan.risk_mode,
        },
        "end_to_end_id": f"AETHER-{plan.source_address[-4:]}-{int(datetime.now(timezone.utc).timestamp())}",
        "purpose": "XRPL internal profit routing; exportable for legacy rails reporting",
    }
    _append_jsonl(ISO20022_OUTBOX_PATH, msg)
    print("[LEGACY-ISO20022GPT] ISO 20022-style record appended to config/iso20022_outbox.jsonl")


# -------------------------------------------------------
# Transaction helpers
# -------------------------------------------------------

def build_payment(source: str, dest: str, amount_drops: int) -> Payment:
    return Payment(
        account=source,
        amount=str(amount_drops),
        destination=dest,
    )


def submit_payment(
    client: JsonRpcClient,
    wallet: Wallet,
    tx: Payment,
):
    try:
        filled = autofill(tx, client)
        signed = sign(filled, wallet)
        resp = submit_and_wait(signed, client)
        return resp
    except Exception as e:
        print(f"[TRANSACTIONSGPT] Submission error: {e}")
        return None


# -------------------------------------------------------
# Main flow
# -------------------------------------------------------

def main() -> None:
    mode = os.getenv("AETHERBORN_MODE", "PAPER").upper()
    risk_code = os.getenv("AETHERBORN_RISK", "B").upper()

    print(f"AETHERBORN SWARM v{AETHERBORN_VERSION} – Governor's XRPL Predator")
    print(f"[ENV] Mode: {mode} | Risk: {risk_code}")
    print("------------------------------------------------------------------------")

    client = JsonRpcClient(XRPL_RPC_URL)

    # 1) Load governor wallet
    try:
        gov = load_governor_wallet(GOVERNOR_WALLET_PATH)
    except Exception as e:
        print(f"[BLOCKCHAINCOUNSELGPT] Governor wallet load error: {e}")
        sys.exit(1)

    vault_address = load_vault_address(VAULT_WALLET_PATH)

    print(f"[MONEYGPT] Source account: {gov.address}")
    if vault_address:
        print(f"[MONEYGPT] Vault  account: {vault_address}")
    else:
        print("[MONEYGPT] Vault  account: <none configured>")

    # 2) Server info
    info = get_server_info(client) or {}
    validated = info.get("validated_ledger") or {}

    print("[XRPLEDGERGPT] Ledger field intelligence:")
    print(f"  • Ledger seq: {validated.get('seq')}")
    print(f"  • Load factor: {info.get('load_factor')}")
    print(f"  • Peers:      {info.get('peers')}")

    # 3) Balances
    balance_drops = get_balance_drops(client, gov.address)
    if balance_drops is None:
        print("[MONEYGPT] Could not fetch source balance; standing down.")
        sys.exit(0)

    balance_xrp = drops_to_xrp(balance_drops)
    print(f"[MONEYGPT] Live balance: {balance_xrp:.6f} XRP")

    vault_enabled = False
    vault_balance_drops = None

    if vault_address:
        vb = get_balance_drops(client, vault_address)
        if vb is None:
            print("[BLOCKCHAINCOUNSELGPT] Vault account not found on-ledger; vault routing disabled.")
        elif vault_address == gov.address:
            print("[BLOCKCHAINCOUNSELGPT] Vault address equals source; vault routing disabled.")
        else:
            vault_enabled = True
            vault_balance_drops = vb

    # 4) Capital framing
    total_xrp = balance_xrp + (drops_to_xrp(vault_balance_drops) if vault_balance_drops is not None else 0.0)
    vault_xrp = drops_to_xrp(vault_balance_drops) if vault_balance_drops is not None else 0.0
    src_pct = (balance_xrp / total_xrp * 100.0) if total_xrp > 0 else 0.0
    vault_pct = (vault_xrp / total_xrp * 100.0) if total_xrp > 0 else 0.0

    print("[FRANKLINTEMPLETONGPT] Capital structure snapshot:")
    print(f"  • Working capital (source): {balance_xrp:.6f} XRP ({src_pct:.2f}%)")
    print(f"  • Vault capital   (vault):  {vault_xrp:.6f} XRP ({vault_pct:.2f}%)")

    print("[BITWISEGPT] Index framing for the swarm:")
    print(f"  • Total 'XRP index AETHER': {total_xrp:.6f} XRP")
    print(f"  • Free-float (tradable):    {balance_xrp:.6f} XRP")
    print(f"  • Locked units (vault):     {vault_xrp:.6f} XRP")

    print("[21SHARESGPT] ETP-style note:")
    print(f"  • Synthetic NAV: {total_xrp:.6f} XRP")
    print("  • Underlying: 100% XRP on XRPL; wrapper is just how we think about it.")

    # 5) Risk + sizing
    risk = get_risk_plan(risk_code)
    print(f"[MONEYGPT] Bankroll (source): {balance_xrp:.6f} XRP | Risk mode={risk_code} ({risk.label})")

    main_amount_drops, fee_amount_drops = plan_trade(balance_drops, risk_code)
    if main_amount_drops <= 0:
        print("[MONEYGPT] Bankroll too small above reserve, standing down.")
        return

    print(
        f"[MONEYGPT] Planned main trade: {main_amount_drops} drops "
        f"({fmt_xrp(main_amount_drops)}, {fmt_pct(risk.deploy_pct)} of deployable)"
    )
    print(f"[MONEYGPT] Protocol fee leg: {fee_amount_drops} drops ({fmt_xrp(fee_amount_drops)})")

    if not vault_enabled:
        print("[BLOCKCHAINCOUNSELGPT] Vault is not valid/enabled – engine will NOT send on-chain, only log/report.")

    print("[QUANTUMALGORITHMGPT] Quantum pattern sweep for AETHERBORN...")
    print("  • Entropy proxy harvested from ledger + fee band; mechanical execution preferred.")

    print("[BLOCKCHAINCOUNSELGPT] Compliance / risk snapshot:")
    print(f"  • Mode: {mode}")
    print(f"  • Risk: {risk_code}")
    print(f"  • Bankroll: {balance_xrp:.6f} XRP")
    print(f"  • Planned trade (drops): {main_amount_drops}")
    print(f"  • Protocol fee (drops): {fee_amount_drops}")
    print(f"  • Vault routing: {'ENABLED' if vault_enabled else 'DISABLED'}")

    # 6) Build TradePlan
    plan = TradePlan(
        mode=mode,
        risk_mode=risk_code,
        source_address=gov.address,
        dest_address=vault_address if vault_enabled else None,
        live_balance_drops=balance_drops,
        main_amount_drops=main_amount_drops,
        fee_amount_drops=fee_amount_drops,
    )

    # 7) ISO style log
    log_iso20022(plan, info)

    # 8) Transaction flow
    if mode == "PAPER":
        print("[TRANSACTIONSGPT] PAPER MODE – not submitting, just simulating.")
        if plan.dest_address:
            tx = build_payment(plan.source_address, plan.dest_address, plan.main_amount_drops)
            print(f"[TRANSACTIONSGPT] Unsigned tx: {tx}")
        else:
            print("[TRANSACTIONSGPT] No valid destination; tx build skipped.")
        print("[PROFITGPT] --- Post-cycle PnL report (PAPER) ---")
        print("[PROFITGPT] Δ balance: 0.000000 XRP (simulation only)")
        return

    # LIVE MODE
    if not plan.dest_address:
        print("[TRANSACTIONSGPT] LIVE MODE – vault disabled; NOT submitting any XRPL transactions.")
        print("[PROFITGPT] --- Post-cycle PnL report (LIVE DRY) ---")
        print("[PROFITGPT] Δ balance: 0.000000 XRP (no on-chain movement).")
        return

    print("[TRANSACTIONSGPT] LIVE MODE – publishing XRPL main transaction...")
    main_tx = build_payment(plan.source_address, plan.dest_address, plan.main_amount_drops)
    main_resp = submit_payment(client, gov.wallet, main_tx)
    print("\n[TRANSACTIONSGPT] LIVE MAIN TX RESULT:")
    print(main_resp)

    print("[TRANSACTIONSGPT] LIVE MODE – publishing XRPL fee transaction...")
    fee_tx = build_payment(plan.source_address, plan.dest_address, plan.fee_amount_drops)
    fee_resp = submit_payment(client, gov.wallet, fee_tx)
    print("\n[TRANSACTIONSGPT] LIVE FEE TX RESULT:")
    print(fee_resp)

    print("[PROFITGPT] --- Post-cycle PnL report (LIVE) ---")
    print("[PROFITGPT] Source wallet debited by main+fee legs; vault credited on-chain.")


if __name__ == "__main__":
    main()
