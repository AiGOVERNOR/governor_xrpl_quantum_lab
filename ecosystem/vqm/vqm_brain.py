from typing import Any, Dict, List

from ecosystem.telemetry.mainnet_watcher import MainnetWatcher
from ecosystem.tools.tool_registry import ToolRegistry, registry as global_registry
from ecosystem.proposals.proposal_engine import ProposalEngine
from ecosystem.policy.policy_engine import PolicyEngine
from ecosystem.safety.safety_guardrails import sanitize_proposal, validate_safe


class VQMEcosystemBrain:
    """
    High-level AI VQM brain:
    - reads XRPL mainnet state
    - consults tools
    - generates proposals
    - applies policy and safety guardrails

    All in "proposal-only" mode: no signing, no trading.
    """

    def __init__(
        self,
        watcher: MainnetWatcher | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.watcher = watcher or MainnetWatcher()
        self.registry = registry or global_registry
        self.proposal_engine = ProposalEngine(self.registry)
        self.policy = PolicyEngine()

        # Seed some baseline tools into the registry (idempotent)
        if self.registry.get("fee_vqm_tool") is None:
            self.registry.register(
                name="fee_vqm_tool",
                category="fee",
                metadata={"description": "Dynamic XRPL fee band advisor."},
            )
        if self.registry.get("stream_pay_tool") is None:
            self.registry.register(
                name="stream_pay_tool",
                category="payment_protocol",
                metadata={"description": "XRPL StreamPay (salary/stream) protocol logic."},
            )
        if self.registry.get("escrow_milestone_tool") is None:
            self.registry.register(
                name="escrow_milestone_tool",
                category="escrow",
                metadata={"description": "Milestone escrow layout planner."},
            )

    def pulse(self) -> Dict[str, Any]:
        """
        Main "heartbeat" of the ecosystem.

        Returns a dict safe to expose via API / CLI.
        """
        network = self.watcher.fetch_snapshot()
        tools = self.registry.as_dict()

        raw_proposals = self.proposal_engine.generate_all(network)
        safe_proposals: List[Dict[str, Any]] = []

        for p in raw_proposals:
            # policy first
            p_with_policy = self.policy.apply(p)
            # safety guardrails
            p_sanitized = sanitize_proposal(p_with_policy)

            if not validate_safe(p_sanitized):
                # Paranoid bail-out; skip if anything looks off
                continue

            safe_proposals.append(p_sanitized)

        return {
            "network_state": {
                "ledger_seq": network.ledger_seq,
                "load_factor": network.load_factor,
                "txn_base_fee": network.txn_base_fee,
                "txn_median_fee": network.txn_median_fee,
                "recommended_fee_drops": network.recommended_fee_drops,
            },
            "tools": tools,
            "proposals": safe_proposals,
        }
