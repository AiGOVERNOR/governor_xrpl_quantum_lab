import requests
import json

MAINNET = "https://s1.ripple.com:51234/"
TESTNET = "https://s.altnet.rippletest.net:51234/"

def xrpl(method, params=None, network="mainnet"):
    url = MAINNET if network == "mainnet" else TESTNET
    body = {
        "method": method,
        "params": [params or {}]
    }
    r = requests.post(url, json=body, timeout=10)
    return r.json()

# Example:
# print(xrpl("server_info"))
