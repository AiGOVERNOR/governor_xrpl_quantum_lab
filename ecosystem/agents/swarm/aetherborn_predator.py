# ecosystem/agents/swarm/aetherborn_predator.py

from __future__ import annotations

from typing import Dict, Any

from .swarmbrain import SwarmBrain
from .predator_kernel import PredatorKernel
from .aetherborn_hivemind import AetherbornHiveMind


class AetherbornPredator:
    """
    Thin wrapper that connects SwarmBrain + PredatorKernel + HiveMind.
    Produces a scalar score for a path taking into account:
      - raw edge
      - path length
      - venue risk
      - profile risk constraints
    """

    def __init__(
        self,
        brain: SwarmBrain,
        kernel: PredatorKernel,
        hivemind: AetherbornHiveMind,
    ) -> None:
        self.brain = brain
        self.kernel = kernel
        self.hivemind = hivemind

    def score_path(self, raw_path: Dict[str, Any]) -> float:
        profile = self.hivemind.get_active_profile()

        hops = raw_path.get("hops", [])
        hop_count = len(hops)
        net_return = float(raw_path.get("net_return", 1.0))  # multiplier
        gross_return = float(raw_path.get("gross_return", net_return))

        # base score from kernel (volatility, venue weights, etc.)
        base_score = self.kernel.score_path(raw_path)

        # penalty: too many hops vs profile limit
        hop_penalty = 0.0
        if hop_count > profile.max_hop_count:
            hop_penalty = (hop_count - profile.max_hop_count) * 0.25

        # edge-based bonus: favor net_return > 1
        edge_bonus = (net_return - 1.0) * 50.0  # scale factor

        # venue risk: simple aggregator over hops
        venue_penalty = 0.0
        for hop in hops:
            venue = hop.get("venue", "UNKNOWN")
            if "AMM" in venue:
                venue_penalty += 0.02
            if "DEX" in venue:
                venue_penalty += 0.01

        # risk_mode influence
        risk_factor = {
            "A": 0.5,
            "B": 0.8,
            "C": 1.0,
            "D": 1.2,
            "E": 1.4,
        }.get(profile.risk_mode, 1.0)

        score = (base_score + edge_bonus - hop_penalty - venue_penalty) * risk_factor

        # avoid negative explosion
        if gross_return <= 0:
            score -= 10.0

        return float(score)
