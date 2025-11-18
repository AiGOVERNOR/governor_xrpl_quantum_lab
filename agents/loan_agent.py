from .base import VQMAgent

class LoanAgent(VQMAgent):
    @property
    def name(self): return "LoanAgent"
    @property
    def role(self): return "loans"

    def mission(self):
        return "Dynamic credit models + micro-loan AI simulations."

    def tools(self):
        return ["Credit Engine", "Micro Loan Fabric"]
