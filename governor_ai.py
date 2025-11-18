import json

from vqm.kernel import QuantumKernel
from vqm.problems import ProblemSpec

from agents.infra_agent import InfraIntelligenceAgent
from agents.banking_agent import BankingAgent
from agents.mortgage_agent import MortgageAgent
from agents.loan_agent import LoanAgent
from agents.fee_agent import FeeAgent

registry = {
    "InfraIntelligenceAgent": InfraIntelligenceAgent,
    "BankingAgent": BankingAgent,
    "MortgageAgent": MortgageAgent,
    "LoanAgent": LoanAgent,
    "FeeAgent": FeeAgent
}

def main():
    cfg = json.load(open("config/agents.json"))
    kernel = QuantumKernel(seed=42)

    agents = []
    for a in cfg["agents"]:
        cls = registry[a["class"]]
        agents.append(cls(a, kernel))

    print("=== AGENT PLANS ===")
    for ag in agents:
        print(json.dumps(ag.plan(), indent=2))

    print("\n=== AGENT STRATEGIES ===")
    for ag in agents:
        problem = {"domain": ag.role}
        print(json.dumps(ag.run(problem), indent=2))

if __name__ == "__main__":
    main()
