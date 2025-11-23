# ecosystem/agents/profit_agent_core.py

from typing import Any, Dict, List

from ecosystem.tx.intents import TxIntent
from ecosystem.flow_engine import build_default_flow_engine


class ProfitAgentCore:
    """
    Core brain for the Governor Profit Agent.

    Mode E (full autonomous multi-strategy), but:
    - Only PLANS transactions (no signing, no submission).
    - Uses Flow Engine + TxIntent to generate execution plans.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.engine = build_default_flow_engine()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _accounts(self) -> Dict[str, str]:
        accounts_cfg = self.config.get("accounts", {})
        return {
            "source": accounts_cfg.get("source_account", "rGovernorSourceXRP"),
            "vault": accounts_cfg.get("profit_vault_account", "rGovernorProfitVault"),
        }

    def _modes(self) -> Dict[str, bool]:
        # Default: all strategies active in Mode E
        default = {
            "arbitrage": True,
            "fee_sniper": True,
            "liquidity_routing": True,
            "yield": True,
        }
        user = self.config.get("modes", {})
        merged = default.copy()
        merged.update(user)
        return merged

    def _risk_cfg(self) -> Dict[str, Any]:
        # Very small, safe demo amounts by default
        default = {
            "arbitrage_probe_drops": 500_000,
            "fee_sniper_amount_drops": 1_000_000,
            "routing_amount_drops": 2_000_000,
            "yield_amount_drops": 1_500_000,
        }
        user = self.config.get("risk", {})
        merged = default.copy()
        merged.update(user)
        return merged

    # ------------------------------------------------------------------
    # Intent builders (all simple payments for now)
    # ------------------------------------------------------------------
    def _build_simple_payment_intent(self, amount_drops: int, memo: str) -> TxIntent:
        accounts = self._accounts()
        return TxIntent.simple_payment(
            amount_drops=amount_drops,
            source_account=accounts["source"],
            destination_account=accounts["vault"],
        )

    # ------------------------------------------------------------------
    # Strategy entry points
    # ------------------------------------------------------------------
    def _run_arbitrage_probe(self, risk: Dict[str, Any]) -> Dict[str, Any]:
        amount = int(risk.get("arbitrage_probe_drops", 500_000))
        intent = self._build_simple_payment_intent(amount, memo="arbitrage_probe")
        plan = self.engine.plan_flow(intent)
        return {"strategy": "arbitrage_probe", "intent": intent.as_dict(), "plan": plan}

    def _run_fee_sniper(self, risk: Dict[str, Any]) -> Dict[str, Any]:
        amount = int(risk.get("fee_sniper_amount_drops", 1_000_000))
        intent = self._build_simple_payment_intent(amount, memo="fee_sniper")
        plan = self.engine.plan_flow(intent)
        return {"strategy": "fee_sniper", "intent": intent.as_dict(), "plan": plan}

    def _run_liquidity_routing(self, risk: Dict[str, Any]) -> Dict[str, Any]:
        # In a future version this would fan out to multileg/AMM routing.
        amount = int(risk.get("routing_amount_drops", 2_000_000))
        intent = self._build_simple_payment_intent(amount, memo="liquidity_routing")
        plan = self.engine.plan_flow(intent)
        return {"strategy": "liquidity_routing", "intent": intent.as_dict(), "plan": plan}

    def _run_yield_harvest(self, risk: Dict[str, Any]) -> Dict[str, Any]:
        amount = int(risk.get("yield_amount_drops", 1_500_000))
        intent = self._build_simple_payment_intent(amount, memo="yield_harvest")
        plan = self.engine.plan_flow(intent)
        return {"strategy": "yield_harvest", "intent": intent.as_dict(), "plan": plan}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run_all_strategies_once(self) -> List[Dict[str, Any]]:
        """
        Mode E: run all enabled strategies once, return their plans.
        """
        modes = self._modes()
        risk = self._risk_cfg()

        results: List[Dict[str, Any]] = []

        if modes.get("arbitrage", False):
            try:
                results.append(self._run_arbitrage_probe(risk))
            except Exception as exc:  # noqa: BLE001
                results.append({"strategy": "arbitrage_probe", "error": repr(exc)})

        if modes.get("fee_sniper", False):
            try:
                results.append(self._run_fee_sniper(risk))
            except Exception as exc:  # noqa: BLE001
                results.append({"strategy": "fee_sniper", "error": repr(exc)})

        if modes.get("liquidity_routing", False):
            try:
                results.append(self._run_liquidity_routing(risk))
            except Exception as exc:  # noqa: BLE001
                results.append({"strategy": "liquidity_routing", "error": repr(exc)})

        if modes.get("yield", False):
            try:
                results.append(self._run_yield_harvest(risk))
            except Exception as exc:  # noqa: BLE001
                results.append({"strategy": "yield_harvest", "error": repr(exc)})

        # Failsafe: always return *something*
        if not results:
            try:
                fallback_intent = self._build_simple_payment_intent(1_000_000, memo="fallback")
                fallback_plan = self.engine.plan_flow(fallback_intent)
                results.append(
                    {
                        "strategy": "fallback",
                        "intent": fallback_intent.as_dict(),
                        "plan": fallback_plan,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append({"strategy": "fallback", "error": repr(exc)})

        return results
