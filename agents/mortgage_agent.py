from .base import VQMAgent

class MortgageAgent(VQMAgent):
    @property
    def name(self): return "MortgageAgent"
    @property
    def role(self): return "mortgage"

    def mission(self):
        return "Mortgage passports + tokenized property concepts."

    def tools(self):
        return ["Mortgage Passport", "Property Tokenizer"]
