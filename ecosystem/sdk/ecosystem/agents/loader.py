from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_CODE_VERSION = "1.0.0"

AGENT_CONFIG_PATH = (
    Path(__file__).resolve().parent / "profit_agent_v1.json"
)


# ---------------------------------------------------------------------------
# Dataclasses for typed config access
# ---------------------------------------------------------------------------

@dataclass
class TriggerConfig:
    median_fee_max: int = 50          # drops
    max_load_factor: float = 1.2
    min_spread_percent: float = 0.3   # reserved for future use


@dataclass
class ConstraintConfig:
    max_risk_level: int = 2
    balance_fraction: float = 0.20    # 20% of free balance at most


@dataclass
class ActionConfig:
    mode: str = "best_available"
    protocols: list[str] = None
    execute_only_if_profitable: bool = True
    log_path: str = "governor_xrpl_quantum_lab/logs/profit_agent/"

    def __post_init__(self) -> None:
        if self.protocols is None:
            self.protocols = ["simple_payment_v2", "multileg_v2"]


@dataclass
class MetadataConfig:
    creator: str = "Governor"
    version: str = AGENT_CODE_VERSION
    note: str = "Autonomous, constrained profit execution agent"
    last_upgraded_from: str | None = None


@dataclass
class ProfitAgentConfig:
    kind: str = "automated_profit_agent"
    trigger: TriggerConfig = TriggerConfig()
    constraints: ConstraintConfig = ConstraintConfig()
    action: ActionConfig = ActionConfig()
    metadata: MetadataConfig = MetadataConfig()

    # ------------------------------------------------------------------ #
    # Serialization helpers
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "trigger": asdict(self.trigger),
            "constraints": asdict(self.constraints),
            "action": asdict(self.action),
            "metadata": asdict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ProfitAgentConfig":
        """
        Self-healing constructor: merges raw dict with safe defaults.
        Any missing or malformed fields fall back to defaults.
        """
        default = cls()

        def get_nested(d: Dict[str, Any], key: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
            val = d.get(key, {})
            return val if isinstance(val, dict) else fallback

        # Top-level kind
        kind = raw.get("kind", default.kind)

        # Nested blocks
        trig_raw = get_nested(raw, "trigger", asdict(default.trigger))
        cons_raw = get_nested(raw, "constraints", asdict(default.constraints))
        act_raw = get_nested(raw, "action", asdict(default.action))
        meta_raw = get_nested(raw, "metadata", asdict(default.metadata))

        trigger = TriggerConfig(
            median_fee_max=int(trig_raw.get("median_fee_max", default.trigger.median_fee_max)),
            max_load_factor=float(trig_raw.get("max_load_factor", default.trigger.max_load_factor)),
            min_spread_percent=float(trig_raw.get("min_spread_percent", default.trigger.min_spread_percent)),
        )

        constraints = ConstraintConfig(
            max_risk_level=int(cons_raw.get("max_risk_level", default.constraints.max_risk_level)),
            balance_fraction=float(cons_raw.get("balance_fraction", default.constraints.balance_fraction)),
        )

        protocols = act_raw.get("protocols", None)
        if not isinstance(protocols, list):
            protocols = default.action.protocols

        action = ActionConfig(
            mode=str(act_raw.get("mode", default.action.mode)),
            protocols=[str(p) for p in protocols],
            execute_only_if_profitable=bool(
                act_raw.get("execute_only_if_profitable", default.action.execute_only_if_profitable)
            ),
            log_path=str(act_raw.get("log_path", default.action.log_path)),
        )

        # Self-upgrade of metadata.version
        raw_version = str(meta_raw.get("version", default.metadata.version))
        if raw_version != AGENT_CODE_VERSION:
            last_from = raw_version
            raw_version = AGENT_CODE_VERSION
        else:
            last_from = meta_raw.get("last_upgraded_from", None)

        metadata = MetadataConfig(
            creator=str(meta_raw.get("creator", default.metadata.creator)),
            version=raw_version,
            note=str(meta_raw.get("note", default.metadata.note)),
            last_upgraded_from=last_from,
        )

        return cls(
            kind=kind,
            trigger=trigger,
            constraints=constraints,
            action=action,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Disk I/O helpers
# ---------------------------------------------------------------------------

def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def default_config() -> ProfitAgentConfig:
    return ProfitAgentConfig()


def load_profit_agent_config(path: Path | None = None) -> ProfitAgentConfig:
    """
    Load the profit agent config from disk.

    - If the file is missing, a default config is created.
    - If the file is corrupted or partially invalid, we fall back to
      defaults and repair as much as possible.
    - If the on-disk version is older than the code version, the
      metadata.version field is bumped and last_upgraded_from is set.
    """
    cfg_path = path or AGENT_CONFIG_PATH
    _ensure_parent_dir(cfg_path)

    raw: Dict[str, Any] | None = None
    healed = False

    if cfg_path.exists():
        try:
            text = cfg_path.read_text(encoding="utf-8")
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                raw = loaded
            else:
                healed = True
        except Exception:
            # Corrupt JSON -> we will heal to defaults
            healed = True

    if raw is None:
        # Missing or corrupt file -> start from defaults
        cfg = default_config()
        healed = True
    else:
        cfg = ProfitAgentConfig.from_dict(raw)

    # Self-upgrade: make sure metadata.version matches code version
    if cfg.metadata.version != AGENT_CODE_VERSION:
        cfg.metadata.last_upgraded_from = cfg.metadata.version
        cfg.metadata.version = AGENT_CODE_VERSION
        healed = True

    # Persist healed / upgraded config
    if healed:
        cfg_path.write_text(json.dumps(cfg.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    return cfg


def save_profit_agent_config(cfg: ProfitAgentConfig, path: Path | None = None) -> None:
    """
    Save the given config back to disk.
    """
    cfg_path = path or AGENT_CONFIG_PATH
    _ensure_parent_dir(cfg_path)
    cfg_path.write_text(json.dumps(cfg.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
