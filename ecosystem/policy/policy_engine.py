from typing import Any, Dict


class PolicyEngine:
    """
    Simple policy gatekeeper.

    This does NOT sign or broadcast anything.
    It only tags proposals and enforces high-level constraints.
    """

    def __init__(self) -> None:
        # Hard-coded guardrails for now
        self.rules = {
            "allow_trading": False,
            "allow_autonomous_signing": False,
            "max_risk_level": 3,  # 0-5, where 5 is wild
        }

    def apply(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a proposal with policy tags and enforce basic constraints.
        """
        p = dict(proposal)  # shallow copy

        # Ensure execution mode is "proposal_only"
        p.setdefault("execution_mode", "proposal_only")

        # No trading allowed
        if p.get("category") == "trading":
            p["policy_status"] = "rejected"
            p["policy_reason"] = "Trading actions are not allowed by policy."
            return p

        # No autonomous signing
        if p.get("requires_signing", False):
            p["policy_status"] = "rejected"
            p["policy_reason"] = "Autonomous signing is not allowed."
            return p

        # Risk level control
        risk = int(p.get("risk_level", 1))
        if risk > self.rules["max_risk_level"]:
            p["policy_status"] = "rejected"
            p["policy_reason"] = f"Risk level {risk} exceeds configured maximum."
            return p

        # All good
        p["policy_status"] = "allowed"
        p.setdefault("policy_reason", "Within configured policy envelope.")
        return p
