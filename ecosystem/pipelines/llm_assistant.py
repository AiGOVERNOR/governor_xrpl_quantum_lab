"""
Pipeline F — LLM Assistant
Explains VQM policy decisions in human-readable form.
"""

class LLMAssistant:

    def explain(self, policy):
        mode = policy["mode"]

        explanations = {
            "normal": "Network stable; no changes required.",
            "conserve_resources": "High load detected; recommend conservative operations.",
            "fee_pressure": "Fee pressure rising; recommend dynamic adjustments.",
        }

        return {
            "explanation": explanations.get(mode, "Unknown mode"),
            "policy_id": policy["id"],
            "human_context": f"Ledger {policy['payload']['ledger']}, Recommended Fee {policy['payload']['recommended_fee']} drops"
        }
