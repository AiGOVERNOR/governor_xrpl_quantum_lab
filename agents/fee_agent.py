from .base import VQMAgent

class FeeAgent(VQMAgent):
    @property
    def name(self): return "FeeAgent"
    @property
    def role(self): return "fees"

    def mission(self):
        return "Fee prediction + gasless-feel routing frameworks."

    def tools(self):
        return ["Fee Predictor", "Gasless Router"]
