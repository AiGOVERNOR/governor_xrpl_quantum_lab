# ecosystem/agents/swarm/aetherborn_router.py

"""
AETHERBORN SWARM – Multi-Hop Router (v1, CLOB-first)
----------------------------------------------------

This module designs payment *routes* for the swarm.

Phase 1:
    • Direct L1 XRPL payment (XRP -> XRP vault)
    • Skeleton for future multi-hop DEX/AMM/LP routing

Future phases:
    • XRPL AMM pools (amm_info)
    • LP tokens and rebalancing
    • Hooks / Xahau smart-contract mediated flows
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from xrpl.clients import JsonRpcClient

from .aetherborn_orderbook_feeder import OrderbookFeeder


@dataclass
class RouteLeg:
    leg_type: str          # "DIRECT", "CLOB", "AMM"
    from_asset: str        # e.g. "XRP", "USD.rIssuer..."
    to_asset: str
    via: str               # "XRPL-CLOB", "XRPL-AMM", "LP", "HOOK"
    est_input_drops: int
    est_output_drops: int
    notes: str = ""


@dataclass
class RoutePlan:
    route_id: str
    source_account: str
    destination_account: str
    input_drops: int
    est_output_drops: int
    legs: List[RouteLeg]
    risk_band: str
    mode: str
    commentary: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["legs"] = [asdict(leg) for leg in self.legs]
        return d


class AetherbornRouter:
    """
    Multi-hop router for AETHERBORN SWARM.

    v1 – mostly planning / telemetry:
        • Direct L1 route
        • Pretty, inspectable structure
        • Hooks for future AMM / LP / smart-contract upgrade
    """

    def __init__(self, client: JsonRpcClient) -> None:
        self.client = client
        self.orderbooks = OrderbookFeeder(client)

    def plan_route(
        self,
        source_account: str,
        vault_account: str,
        amount_drops: int,
        *,
        risk_band: str = "B",
        mode: str = "PAPER",
        prefer_multihop: bool = False,
    ) -> RoutePlan:
        """
        Compute a route for moving `amount_drops` from source to vault.

        For now:
            • If prefer_multihop=False → direct L1 payment (single leg)
            • If prefer_multihop=True  → still direct, but returns
              `commentary` explaining where multi-hop would attach.
        """

        commentary: List[str] = []
        commentary.append(
            f"Router invoked with amount={amount_drops} drops, "
            f"risk_band={risk_band}, mode={mode}, prefer_multihop={prefer_multihop}"
        )

        # --- Phase 1: direct L1 route (baseline, safe) ---
        direct_leg = RouteLeg(
            leg_type="DIRECT",
            from_asset="XRP",
            to_asset="XRP",
            via="XRPL-L1",
            est_input_drops=amount_drops,
            est_output_drops=amount_drops,
            notes="Direct XRPL payment source -> vault",
        )

        # Placeholder for multi-hop analysis – we keep it non-fatal
        if prefer_multihop:
            commentary.append(
                "Multi-hop preference set. In v1, router simulates multihop "
                "structure but executes/returns direct route."
            )
            commentary.append(
                "Future hooks: inspect XRPL AMM pools, IOU books, LP tokens, "
                "simulate path: XRP -> IOU1 -> IOU2 -> XRP(vault)."
            )

        plan = RoutePlan(
            route_id=f"AETHER-{source_account[-4:]}-{vault_account[-4:]}",
            source_account=source_account,
            destination_account=vault_account,
            input_drops=amount_drops,
            est_output_drops=amount_drops,
            legs=[direct_leg],
            risk_band=risk_band,
            mode=mode,
            commentary=commentary,
        )

        self._log_plan(plan)
        return plan

    @staticmethod
    def _log_plan(plan: RoutePlan) -> None:
        print("\n[ROUTERGPT] === Multi-Hop Route Plan ===")
        print(f"[ROUTERGPT] Route ID: {plan.route_id}")
        print(
            f"[ROUTERGPT] {plan.source_account} -> {plan.destination_account} "
            f"| input={plan.input_drops} drops, est_out={plan.est_output_drops} drops"
        )
        print(f"[ROUTERGPT] Mode={plan.mode} | Risk={plan.risk_band}")
        for leg in plan.legs:
            print(
                f"[ROUTERGPT]  • Leg [{leg.leg_type}] {leg.from_asset} -> {leg.to_asset} "
                f"via {leg.via} | in={leg.est_input_drops}, out={leg.est_output_drops}"
            )
            if leg.notes:
                print(f"[ROUTERGPT]    notes: {leg.notes}")
        if plan.commentary:
            print("[ROUTERGPT] Commentary:")
            for line in plan.commentary:
                print(f"[ROUTERGPT]   - {line}")
        print("[ROUTERGPT] === End Route Plan ===\n")
