# ecosystem/agents/swarm/aetherborn_orderbook_feeder.py

"""
AETHERBORN SWARM – Orderbook Feeder (XRPL CLOB)
----------------------------------------------

This module pulls XRPL orderbook snapshots in a swarm-friendly format.
Phase 1: CLOB (Orderbook) only, AMM / LP hooks are TODO.

Usage:
    feeder = OrderbookFeeder(client)
    book = feeder.fetch_orderbook(
        taker_gets_currency="XRP",
        taker_pays_currency="USD",
        taker_pays_issuer="rEXAMPLEISSUER..."
    )
"""

from typing import Any, Dict, List

from xrpl.clients import JsonRpcClient
from xrpl.models.requests import BookOffers


class OrderbookFeeder:
    """
    Thin wrapper around XRPL BookOffers.
    Returns a normalized dict with bids/asks and raw offers.
    """

    def __init__(self, client: JsonRpcClient) -> None:
        self.client = client

    def fetch_orderbook(
        self,
        taker_gets_currency: str,
        taker_pays_currency: str,
        taker_gets_issuer: str = "",
        taker_pays_issuer: str = "",
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Fetch a single orderbook.

        Example:
            XRP -> USD.rIssuer
            taker_gets_currency="XRP"
            taker_pays_currency="USD"
            taker_pays_issuer="rIssuer..."
        """

        print("[ORDERBOOKGPT] Fetching orderbook:")
        print(
            f"  taker_gets={taker_gets_currency}.{taker_gets_issuer or '-'} "
            f"taker_pays={taker_pays_currency}.{taker_pays_issuer or '-'}"
        )

        # Build BookOffers request
        req = BookOffers(
            taker_gets=self._encode_currency(taker_gets_currency, taker_gets_issuer),
            taker_pays=self._encode_currency(taker_pays_currency, taker_pays_issuer),
            limit=limit,
        )

        resp = self.client.request(req)
        offers: List[Dict[str, Any]] = resp.result.get("offers", [])

        print(f"[ORDERBOOKGPT] Got {len(offers)} offers")

        normalized = {
            "pair": {
                "taker_gets": {
                    "currency": taker_gets_currency,
                    "issuer": taker_gets_issuer or None,
                },
                "taker_pays": {
                    "currency": taker_pays_currency,
                    "issuer": taker_pays_issuer or None,
                },
            },
            "raw_offers": offers,
        }

        return normalized

    @staticmethod
    def _encode_currency(currency: str, issuer: str) -> Dict[str, str]:
        """
        Produce a `CurrencyAmount`-style dict for BookOffers.
        """
        if currency.upper() == "XRP":
            return "XRP"
        return {
            "currency": currency,
            "issuer": issuer,
        }
