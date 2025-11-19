from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class NetworkState:
    ledger_seq: int
    txn_base_fee: int
    txn_median_fee: int
    recommended_fee_drops: int
    load_factor: float


@dataclass
class GuardianSnapshot:
    mode: str
    policy_status: Optional[str]
    explanation: Optional[str]
    raw: Dict[str, Any]


@dataclass
class FeeHorizon:
    band: str
    horizon_seconds: int
    trend_short: str
    trend_long: str
    raw: Dict[str, Any]


@dataclass
class MeshIntentSnapshot:
    mode: str
    priority: str
    band: str
    raw: Dict[str, Any]


@dataclass
class VQMFullState:
    pipeline_version: str
    timestamp: str
    network_state: NetworkState
    guardian: Optional[GuardianSnapshot]
    fee_horizon: Optional[FeeHorizon]
    mesh_intent: Optional[MeshIntentSnapshot]
    tools: List[Dict[str, Any]]
    raw: Dict[str, Any]
