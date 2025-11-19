from vqm.kernel import QuantumKernel
from vqm.problems import VQMConfig

from agents.infra_agent import InfraIntelligenceAgent
from agents.banking_agent import BankingAgent
from agents.mortgage_agent import MortgageAgent
from agents.loan_agent import LoanAgent
from agents.fee_agent import FeeAgent


def load_agent(agent_cls):
    """
    Creates a fully initialized VQM agent using the required
    (config, kernel) constructor signature.
    """
    kernel = QuantumKernel()
    config = VQMConfig()

    return agent_cls(config=config, kernel=kernel)


def load_all_agents():
    return {
        "infra": load_agent(InfraIntelligenceAgent),
        "banking": load_agent(BankingAgent),
        "mortgage": load_agent(MortgageAgent),
        "loans": load_agent(LoanAgent),
        "fees": load_agent(FeeAgent),
    }

