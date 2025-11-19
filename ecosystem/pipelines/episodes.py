from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FeePressureEpisode:
    """
    A simple summary of a fee-pressure episode:

    - mode: guardian mesh mode at the end of the episode
    - start_ledger / end_ledger: inclusive ledger range
    - start_time / end_time: ISO timestamps from snapshots
    - median_fee: median fee at the end of the episode
    - load_factor: load factor at the end of the episode
    - snapshots: raw snapshots that belong to this episode
    """

    mode: str
    start_ledger: int
    end_ledger: int
    start_time: str
    end_time: str
    median_fee: int
    load_factor: float
    snapshots: List[Dict[str, Any]]


class EpisodeDetector:
    """
    Dumb-but-useful fee-pressure episode detector.

    Rule of thumb:
    - An episode is a consecutive run of snapshots where either:
      * median_fee >= fee_pressure_threshold, OR
      * guardian.mesh.mode in {"fee_pressure", "extreme_pressure"}
    - We only return the LAST qualifying episode if its length
      is at least min_length snapshots.
    """

    def __init__(self, fee_pressure_threshold: int = 5000, min_length: int = 3):
        self.fee_pressure_threshold = fee_pressure_threshold
        self.min_length = min_length

    def detect_last_episode(
        self, snapshots: List[Dict[str, Any]]
    ) -> Optional[FeePressureEpisode]:
        if not snapshots:
            return None

        current: List[Dict[str, Any]] = []

        for snap in snapshots:
            ns = snap.get("network_state", {}) or {}
            guardian = snap.get("guardian", {}) or {}
            mesh = guardian.get("mesh", {}) or {}

            median = (
                ns.get("txn_median_fee")
                or ns.get("txn_median_fee_drops")
                or 0
            )
            mode = mesh.get("mode") or "unknown"

            in_pressure = (
                median >= self.fee_pressure_threshold
                or mode in ("fee_pressure", "extreme_pressure")
            )

            if in_pressure:
                current.append(snap)
            else:
                # Episode just ended
                if len(current) >= self.min_length:
                    return self._build_episode(current)
                current = []

        # Episode may continue to the end
        if len(current) >= self.min_length:
            return self._build_episode(current)

        return None

    def _build_episode(self, snaps: List[Dict[str, Any]]) -> FeePressureEpisode:
        first = snaps[0]
        last = snaps[-1]

        ns_first = first.get("network_state", {}) or {}
        ns_last = last.get("network_state", {}) or {}
        guardian_last = last.get("guardian", {}) or {}
        mesh_last = guardian_last.get("mesh", {}) or {}

        mode = mesh_last.get("mode") or "fee_pressure"

        return FeePressureEpisode(
            mode=mode,
            start_ledger=int(ns_first.get("ledger_seq") or 0),
            end_ledger=int(ns_last.get("ledger_seq") or 0),
            start_time=first.get("timestamp") or "",
            end_time=last.get("timestamp") or "",
            median_fee=int(ns_last.get("txn_median_fee") or 0),
            load_factor=float(ns_last.get("load_factor") or 0.0),
            snapshots=snaps,
        )
