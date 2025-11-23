# ecosystem/agents/swarm/aetherborn_hivemind.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class StrategyProfile:
    name: str
    risk_mode: str           # "A", "B", "C", "D", etc.
    max_leverage: float
    max_hop_count: int
    target_edge_bp: float
    notes: List[str] = field(default_factory=list)


class AetherbornHiveMind:
    """
    Global coordination layer for AETHERBORN SWARM.
    Decides which strategy profile is active, tracks versions, and
    exposes upgrade hooks for self-tuning.
    """

    def __init__(self) -> None:
        self.version = "2.3.0"
        self.swarm_name = "AETHERBORN_SWARM"
        self._profiles: Dict[str, StrategyProfile] = {}
        self.active_profile: StrategyProfile | None = None
        self.telemetry: Dict[str, Any] = {}
        self._init_default_profiles()

    def _init_default_profiles(self) -> None:
        low = StrategyProfile(
            name="low_risk_scalp",
            risk_mode="B",
            max_leverage=1.0,
            max_hop_count=2,
            target_edge_bp=0.5,
            notes=["gentle probing", "fee-aware", "primarily AMM <= 2 hops"],
        )
        normal = StrategyProfile(
            name="normal_predator",
            risk_mode="C",
            max_leverage=1.5,
            max_hop_count=3,
            target_edge_bp=1.0,
            notes=["balanced aggression", "3-hop limit", "prefers deep pools"],
        )
        spicy = StrategyProfile(
            name="high_energy_hunt",
            risk_mode="D",
            max_leverage=2.0,
            max_hop_count=4,
            target_edge_bp=1.5,
            notes=["aggressive", "slippage-tolerant", "only in low-fee regimes"],
        )

        self._profiles[low.name] = low
        self._profiles[normal.name] = normal
        self._profiles[spicy.name] = spicy
        self.active_profile = normal

    # ---------- Profile control ----------

    def set_active_profile(self, name: str) -> StrategyProfile:
        if name not in self._profiles:
            raise ValueError(f"Unknown strategy profile: {name}")
        self.active_profile = self._profiles[name]
        return self.active_profile

    def get_active_profile(self) -> StrategyProfile:
        if self.active_profile is None:
            self.set_active_profile("normal_predator")
        return self.active_profile  # type: ignore[return-value]

    def describe_profiles(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "risk_mode": p.risk_mode,
                "max_leverage": p.max_leverage,
                "max_hop_count": p.max_hop_count,
                "target_edge_bp": p.target_edge_bp,
                "notes": p.notes,
            }
            for name, p in self._profiles.items()
        }

    # ---------- Upgrade hooks (self-modifying config only) ----------

    def register_telemetry(self, key: str, value: Any) -> None:
        self.telemetry[key] = value

    def auto_upgrade_profiles(self) -> None:
        """
        Simple self-adjusting logic:
        if realized PnL is consistently positive and volatility low,
        loosen constraints slightly. If negative, tighten them.
        """
        pnl = float(self.telemetry.get("pnl_30m", 0.0))
        vol = float(self.telemetry.get("pnl_vol_30m", 0.0))

        for p in self._profiles.values():
            if pnl > 0 and vol < 0.001:
                p.target_edge_bp = min(p.target_edge_bp * 1.02, 5.0)
            elif pnl < 0:
                p.max_leverage = max(1.0, p.max_leverage * 0.98)
                p.max_hop_count = max(1, p.max_hop_count - 1)

    def snapshot_state(self) -> Dict[str, Any]:
        active = self.get_active_profile()
        return {
            "version": self.version,
            "swarm_name": self.swarm_name,
            "active_profile": {
                "name": active.name,
                "risk_mode": active.risk_mode,
                "max_leverage": active.max_leverage,
                "max_hop_count": active.max_hop_count,
                "target_edge_bp": active.target_edge_bp,
            },
            "telemetry": dict(self.telemetry),
        }
