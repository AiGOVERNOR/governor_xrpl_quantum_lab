from abc import ABC, abstractmethod

class VQMAgent(ABC):
    def __init__(self, config, kernel):
        self.config = config
        self.kernel = kernel

    @property
    @abstractmethod
    def name(self): ...

    @property
    @abstractmethod
    def role(self): ...

    @abstractmethod
    def mission(self): ...

    @abstractmethod
    def tools(self): ...

    def plan(self):
        return {
            "agent": self.name,
            "role": self.role,
            "mission": self.mission(),
            "tools": self.tools(),
            "self_repair": ["auto-diagnose", "auto-heal"],
            "self_modify": ["optimize", "upgrade"],
            "xrpl_compliance": True
        }

    def run(self, problem):
        return self.kernel.solve(problem)
