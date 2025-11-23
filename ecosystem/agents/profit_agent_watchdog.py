# ecosystem/agents/profit_agent_watchdog.py

import json
import subprocess
from pathlib import Path
from typing import Any, Dict


AGENTS_DIR = Path(__file__).resolve().parent


def _load_config(agent_name: str) -> Dict[str, Any]:
    path = AGENTS_DIR / f"{agent_name}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _save_config(agent_name: str, config: Dict[str, Any]) -> None:
    path = AGENTS_DIR / f"{agent_name}.json"
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, sort_keys=True)
    except Exception:
        # Last resort: if we can't persist, we still return in-memory config
        pass


def run_vqm_doctor() -> Dict[str, Any]:
    """
    Call `python -m ecosystem.cli.vqm_doctor_cli` and parse JSON.
    """
    try:
        proc = subprocess.run(
            ["python", "-m", "ecosystem.cli.vqm_doctor_cli"],
            capture_output=True,
            text=True,
            check=True,
        )
        out = proc.stdout.strip()
        if not out:
            return {"error": "empty_output"}
        return json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}


def _derive_mode_flags(report: Dict[str, Any]) -> Dict[str, bool]:
    """
    Turn doctor diagnostics into strategy toggles.
    """
    modes = {
        "arbitrage": True,
        "fee_sniper": True,
        "liquidity_routing": True,
        "yield": True,
    }

    # If Flow Engine is broken, disable everything (fail safe)
    if not report.get("flow_engine", {}).get("ok", False):
        for k in modes:
            modes[k] = False
        return modes

    # If multileg / protocol_graph look bad, disable advanced routing
    if not report.get("multileg", {}).get("ok", False):
        modes["liquidity_routing"] = False

    if not report.get("protocol_graph", {}).get("ok", False):
        modes["liquidity_routing"] = False

    # If router/sdk are flaky, be conservative with arbitrage
    if not report.get("router_v3", {}).get("ok", False):
        modes["arbitrage"] = False

    if not report.get("sdk_client", {}).get("ok", False):
        modes["arbitrage"] = False

    # Yield + fee_sniper are lowest complexity; they stay on unless FlowEngine is dead
    return modes


def auto_tune_and_persist(agent_name: str, current_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Self-healing step:
    - Runs VQM doctor
    - Infers which strategies are safe
    - Writes updated config back to disk
    - Returns merged config
    """
    base_cfg = dict(_load_config(agent_name))
    base_cfg.update(current_cfg or {})

    report = run_vqm_doctor()
    base_cfg.setdefault("last_health_report", {})
    base_cfg["last_health_report"] = report

    modes = _derive_mode_flags(report)
    merged_modes = {
        "arbitrage": True,
        "fee_sniper": True,
        "liquidity_routing": True,
        "yield": True,
    }
    merged_modes.update(base_cfg.get("modes", {}))
    merged_modes.update(modes)

    base_cfg["modes"] = merged_modes

    _save_config(agent_name, base_cfg)
    return base_cfg
