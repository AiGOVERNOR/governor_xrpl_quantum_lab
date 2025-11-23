# ================================================================
# AETHERBORN SWARM v3.0 - Profit Agent Runner
# Governor’s Autonomous Arbitrage Predator Engine
# ================================================================

import json
import os
import time
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
from xrpl.models.transactions import Payment
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.models.requests import AccountInfo

# ================================================================
# Internal Swarm Components
# ================================================================
from ecosystem.agents.swarm.swarmbrain import SwarmBrain
from ecosystem.agents.swarm.predator_kernel import PredatorKernel

XRPL = "https://s1.ripple.com:51234"
client = JsonRpcClient(XRPL)


# ================================================================
# Load wallet safely
# ================================================================
def load_wallet(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Wallet not found: {path}")

    with open(path) as f:
        data = json.load(f)

    wallet = Wallet(
        public_key=data["public_key"],
        private_key=data["private_key"],
        seed=data["seed"],
    )
    return wallet, data["address"]


# ================================================================
# Live XRPL payment
# ================================================================
def safe_execute(wallet, src, dest, drops):
    tx = Payment(
        account=src,
        destination=dest,
        amount=str(drops),
    )

    tx = autofill(tx, client)
    signed = sign(tx, wallet)
    result = submit_and_wait(signed, client)
    return result


# ================================================================
# Main Aetherborn Swarm runner
# ================================================================
def run():
    print("AETHERBORN SWARM v3.0 — LIVE MODE ONLINE")

    # Load wallets
    source_wallet, source_address = load_wallet("config/governor_wallet.json")
    vault_wallet, vault_address = load_wallet("config/governor_vault_wallet.json")

    # Load Swarm systems
    brain = SwarmBrain()
    predator = PredatorKernel()

    print(f"[MONEYGPT] Source: {source_address}")
    print(f"[MONEYGPT] Vault:  {vault_address}")

    # Query balance
    bal_req = AccountInfo(
        account=source_address,
        ledger_index="validated",
        strict=True,
    )
    bal = client.request(bal_req).result["account_data"]["Balance"]
    xrp_balance = int(bal) / 1_000_000
    print(f"[MONEYGPT] Balance: {xrp_balance} XRP")

    # Swarm chooses trade size
    drops = predator.choose_trade_amount(bal=int(bal))
    print(f"[PROFITGPT] Trade size: {drops} drops")

    # SwarmBrain analyzes network
    brain_status = brain.analyze()
    print(f"[XRPLEDGERGPT] {brain_status}")

    # Execute
    print("[TRANSACTIONSGPT] Publishing live transaction...")
    result = safe_execute(
        wallet=source_wallet,
        src=source_address,
        dest=vault_address,
        drops=drops,
    )

    print("\n[TRANSACTIONSGPT] RESULT:")
    print(result)


if __name__ == "__main__":
    run()
