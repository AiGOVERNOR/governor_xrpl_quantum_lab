# ecosystem/agents/execution.py
# XRPL LIVE EXECUTION ENGINE — 100% Compatible with xrpl-py 4.3.1

from xrpl.clients import JsonRpcClient
from xrpl.models.transactions import Payment
from xrpl.transaction import autofill, sign, submit_and_wait
from xrpl.wallet import Wallet

XRPL_NODE = "https://s1.ripple.com:51234/"
client = JsonRpcClient(XRPL_NODE)


def safe_execute(wallet: Wallet, source_address: str, destination_address: str, amount_drops: int):
    """
    Execute a live XRPL payment using xrpl-py 4.x.
    """

    # Build unsigned transaction
    tx = Payment(
        account=source_address,
        amount=str(amount_drops),
        destination=destination_address,
    )

    # Autofill fees, sequence, ledger index
    tx = autofill(tx, client)

    # Sign locally using the Wallet's keys
    signed_tx = sign(tx, wallet)

    # Submit and wait for validation
    response = submit_and_wait(signed_tx, client)

    return response

