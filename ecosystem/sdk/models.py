from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class VQMState:
    """
    Canonical view of a single VQM pipeline cycle.

    This is a light wrapper around the pipeline_v5 output.
    """
    network_state: Dict[str, Any] = field(default_factory=dict)
    guardian: Dict[str, Any] = field(default_factory=dict)
    heartbeat: Dict[str, Any] = field(default_factory=dict)
    pipeline_version: str = "unknown"

    def safety_summary(self) -> Dict[str, Any]:
        g = self.guardian or {}
        return {
            "pipeline_version": self.pipeline_version,
            "mode": g.get("mode"),
            "safety": g.get("safety"),
            "hard_guarantees": g.get("hard_guarantees"),
        }


@dataclass
class VQMClientConfig:
    """
    Configuration for the VQMClient.

    mode:
      - "local": call pipeline_v5 directly in-process.
      - "http":  call a remote API (e.g., api_vqm.py) over HTTP.
    """
    mode: str = "local"
    base_url: Optional[str] = None
    timeout_seconds: float = 5.0

    def __post_init__(self) -> None:
        if self.mode not in ("local", "http"):
            raise ValueError(f"Unsupported mode: {self.mode!r}")

        if self.mode == "http" and not self.base_url:
            raise ValueError("base_url is required when mode='http'")
