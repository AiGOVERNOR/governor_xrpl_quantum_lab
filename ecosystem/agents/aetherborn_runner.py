# ecosystem/agents/aetherborn_runner.py

from __future__ import annotations

from typing import Any, Dict

from ecosystem.agents.swarm.swarmbrain import SwarmBrain
from ecosystem.agents.swarm.predator_kernel import PredatorKernel
from ecosystem.agents.swarm.aetherborn_engine import AetherbornEngine
from ecosystem.agents.swarm.aetherborn_hivemind import AetherbornHiveMind
from ecosystem.agents.swarm.aetherborn_predator import AetherbornPredator
from ecosystem.agents.swarm.aetherborn_router import AetherbornRouter
from ecosystem.agents.swarm.aetherborn_orderbook_feeder import (
    OrderbookFeeder,
    PairSnapshot,
)
from ecosystem.agents.swarm.aetherborn_autotuning_kernel import AutoTuningKernel


def build_demo_snapshot() -> Dict[str, Any]:
    """
    Purely local demo snapshot – no network calls.
    You can later wire OrderbookFeeder.set_live_callback(...) to XRPL data.
    """
    feeder = OrderbookFeeder()
    feeder.set_static_pairs(
        [
            PairSnapshot(
                venue="XRPL_AMM",
                base="XRP",
                quote="USD",
                bid=0.52,
                ask=0.521,
                liquidity=500_000.0,
                fee_bp=30.0,
            ),
            PairSnapshot(
                venue="XRPL_AMM",
                base="USD",
                quote="SOLO",
                bid=2.0,
                ask=2.01,
                liquidity=100_000.0,
                fee_bp=40.0,
            ),
            PairSnapshot(
                venue="XRPL_DEX",
                base="SOLO",
                quote="XRP",
                bid=3.8,
                ask=3.82,
                liquidity=80_000.0,
                fee_bp=20.0,
            ),
        ]
    )
    return feeder.snapshot()


def run(mode: str = "SIM", bankroll_xrp: float = 10.0) -> None:
    print("AETHERBORN SWARM v2.3 — Aetherborn Runner")
    print(f"[mode] {mode}")
    print(f"[bankroll] {bankroll_xrp} XRP")
    print()

    # Core components
    brain = SwarmBrain()
    kernel = PredatorKernel()
    hivemind = AetherbornHiveMind()
    autotune = AutoTuningKernel()

    predator = AetherbornPredator(brain=brain, kernel=kernel, hivemind=hivemind)
    engine = AetherbornEngine(swarmbrain=brain, predator=kernel)
    router = AetherbornRouter(network="XRPL_MAINNET")

    snapshot = build_demo_snapshot()

    # HiveMind awareness
    hivemind.register_telemetry("pnl_30m", autotune.realized_pnl())
    hivemind.register_telemetry("pnl_vol_30m", 0.0)
    hivemind.auto_upgrade_profiles()

    profile_state = hivemind.snapshot_state()
    print("[HIVEMIND] State:")
    print(profile_state)
    print()

    # Build and choose path
    plans = engine.build_paths(
        market_snapshot=snapshot,
        base_asset="XRP",
        bankroll_xrp=bankroll_xrp,
        max_hops=profile_state["active_profile"]["max_hop_count"],
    )

    if not plans:
        print("[AETHERBORN] No viable paths found in snapshot.")
        return

    best = plans[0]
    print("[AETHERBORN] Best plan:")
    print(f"  net_return: {best.net_return:.6f}x")
    print(f"  edge_bp:    {best.edge_bp:.3f} bp")
    print("  hops:")
    for idx, hop in enumerate(best.hops):
        print(
            f"    [{idx}] {hop.venue} {hop.base}/{hop.quote} "
            f"{hop.side} size={hop.size} price~{hop.expected_price} "
            f"fees={hop.expected_fees} slip={hop.slippage_bp}bp"
        )
    print()

    intents = router.plan_to_intents(best)
    print("[ROUTER] Intents:")
    for intent in intents:
        print("  ", intent)

    if mode.upper() == "LIVE":
        print()
        print("[AETHERBORN] LIVE mode not wired here –")
        print("           integrate these intents with your existing")
        print("           profit_agent_runner / tx flow once you’re happy.")
    else:
        print()
        print("[AETHERBORN] Simulation complete – introspect, tune, then wire into LIVE stack.")


if __name__ == "__main__":
    run()
