from dataclasses import dataclass
from typing import Dict, Any

from xrpl_client import XRPLClient


@dataclass
class FeeSnapshot:
    base_drops: int
    median_drops: int
    open_ledger_drops: int
    load_factor: float


class XRPLFeeEstimator:
    """
    Reads XRPL 'fee' RPC and exposes easy fee recommendations.
    """

    def __init__(self, url: str = "https://s1.ripple.com:51234"):
        self.client = XRPLClient(url=url)

    def fetch_raw(self) -> Dict[str, Any]:
        return self.client.fee()

    def snapshot(self) -> FeeSnapshot:
        result = self.fetch_raw()
        drops = result.get("drops", {})

        base = int(drops.get("base_fee_drops", "10"))
        median = int(drops.get("median_fee_drops", str(base)))
        open_ledger = int(drops.get("open_ledger_fee_drops", str(median)))

        load_factor = float(result.get("load_factor", 1.0))

        return FeeSnapshot(
            base_drops=base,
            median_drops=median,
            open_ledger_drops=open_ledger,
            load_factor=load_factor,
        )

    def recommended_fee_drops(self, safety_multiplier: float = 1.2) -> int:
        snap = self.snapshot()
        fee = int(snap.open_ledger_drops * safety_multiplier)
        return max(fee, snap.median_drops)


def main():
    from rich import print as rprint

    est = XRPLFeeEstimator()
    snap = est.snapshot()

    rprint({"snapshot": snap})
    rprint({"recommended_drops": est.recommended_fee_drops()})


if __name__ == "__main__":
    main()
