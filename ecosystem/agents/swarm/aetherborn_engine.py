# ecosystem/agents/swarm/aetherborn_engine.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .swarmbrain import SwarmBrain
from .predator_kernel import PredatorKernel


@dataclass
class Hop:
    """Represents one leg in a multi-hop path."""
    venue: str                 # e.g. "XRPL_AMM", "XRPL_DEX"
    base: str                  # e.g. "XRP"
    quote: str                 # e.g. "USD", "SOLO"
    side: str                  # "buy" or "sell"
    size: float                # in base units
    expected_price: float      # quote/base
    expected_fees: float       # in quote units
    slippage_bp: float         # slippage in basis points


@dataclass
class PathPlan:
    """Final assembled path with estimated PnL."""
    hops: List[Hop]
    gross_return: float        # ending value in base asset
    net_return: float          # after fees & slippage
    edge_bp: float             # net edge in basis points
    notes: List[str]


class AetherbornEngine:
    """
    Core multi-hop arbitrage planner.
    Uses SwarmBrain to explore and PredatorKernel to score/select paths.
    """

    def __init__(self, swarmbrain: SwarmBrain, predator: PredatorKernel) -> None:
        self.swarmbrain = swarmbrain
        self.predator = predator

    # -------- PUBLIC API --------

    def build_paths(
        self,
        market_snapshot: Dict[str, Any],
        base_asset: str = "XRP",
        bankroll_xrp: float = 1.0,
        max_hops: int = 3,
    ) -> List[PathPlan]:
        """
        Given a unified market snapshot, explore + score candidate paths.
        market_snapshot is intentionally generic so we don't depend
        on any specific XRPL client here.
        """
        # 1) Generate candidate raw paths from SwarmBrain
        candidates = self.swarmbrain.generate_candidate_paths(
            market_snapshot=market_snapshot,
            base_asset=base_asset,
            bankroll=bankroll_xrp,
            max_hops=max_hops,
        )

        # 2) Score with PredatorKernel
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for path in candidates:
            score = self.predator.score_path(path)
            scored.append((score, path))

        scored.sort(key=lambda x: x[0], reverse=True)

        # 3) Convert into PathPlan objects
        plans: List[PathPlan] = []
        for rank, (score, raw_path) in enumerate(scored):
            hops: List[Hop] = []
            notes: List[str] = [f"rank={rank}", f"predator_score={score:.6f}"]

            gross = raw_path.get("gross_return", 1.0)
            net = raw_path.get("net_return", 1.0)
            edge_bp = (net - 1.0) * 10_000.0

            for hop_raw in raw_path.get("hops", []):
                hops.append(
                    Hop(
                        venue=hop_raw.get("venue", "UNKNOWN"),
                        base=hop_raw.get("base", base_asset),
                        quote=hop_raw.get("quote", "UNKNOWN"),
                        side=hop_raw.get("side", "buy"),
                        size=float(hop_raw.get("size", 0.0)),
                        expected_price=float(hop_raw.get("expected_price", 0.0)),
                        expected_fees=float(hop_raw.get("expected_fees", 0.0)),
                        slippage_bp=float(hop_raw.get("slippage_bp", 0.0)),
                    )
                )

            plans.append(
                PathPlan(
                    hops=hops,
                    gross_return=float(gross),
                    net_return=float(net),
                    edge_bp=float(edge_bp),
                    notes=notes,
                )
            )

        return plans

    def best_plan(
        self,
        market_snapshot: Dict[str, Any],
        base_asset: str = "XRP",
        bankroll_xrp: float = 1.0,
        max_hops: int = 3,
        min_edge_bp: float = 1.0,
    ) -> PathPlan | None:
        """
        Convenience helper: return the top plan above a minimum edge threshold.
        """
        plans = self.build_paths(
            market_snapshot=market_snapshot,
            base_asset=base_asset,
            bankroll_xrp=bankroll_xrp,
            max_hops=max_hops,
        )
        if not plans:
            return None

        best = plans[0]
        if best.edge_bp >= min_edge_bp:
            return best
        return None
