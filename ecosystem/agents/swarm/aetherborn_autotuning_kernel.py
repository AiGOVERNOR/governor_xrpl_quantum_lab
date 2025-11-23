# ecosystem/agents/swarm/aetherborn_autotuning_kernel.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PnLSample:
    pnl: float  # realized pnl in base units
    risk_used: float  # fraction of bankroll used (0..1)


@dataclass
class AutoTuningKernel:
    """
    Collects realized PnL samples and adjusts a few knobs over time.
    This is intentionally simple and transparent.
    """

    window_size: int = 64
    samples: List[PnLSample] = field(default_factory=list)
    risk_multiplier: float = 1.0
    edge_multiplier: float = 1.0

    def add_sample(self, pnl: float, risk_used: float) -> None:
        self.samples.append(PnLSample(pnl=pnl, risk_used=risk_used))
        if len(self.samples) > self.window_size:
            self.samples = self.samples[-self.window_size :]

    def realized_pnl(self) -> float:
        return float(sum(s.pnl for s in self.samples))

    def average_risk_used(self) -> float:
        if not self.samples:
            return 0.0
        return float(sum(s.risk_used for s in self.samples) / len(self.samples))

    def retune(self) -> None:
        """
        Very simple logic:
          - If total pnl > 0 and average risk < 0.2: we can be slightly braver.
          - If total pnl < 0: we become more conservative.
        """
        pnl = self.realized_pnl()
        avg_risk = self.average_risk_used()

        if pnl > 0 and avg_risk < 0.2:
            self.risk_multiplier = min(self.risk_multiplier * 1.05, 2.0)
            self.edge_multiplier = max(self.edge_multiplier * 0.98, 0.5)
        elif pnl < 0:
            self.risk_multiplier = max(self.risk_multiplier * 0.95, 0.5)
            self.edge_multiplier = min(self.edge_multiplier * 1.05, 3.0)
