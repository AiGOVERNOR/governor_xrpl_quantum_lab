"""
VQM Problems & Config Module
----------------------------------
Defines the default configuration for all Governor VQM Agents.
"""

class VQMConfig:
    """
    Minimal configuration object used by VQM agents.
    Expandable as the mesh evolves.
    """
    def __init__(self, domain: str = "generic", params=None):
        self.domain = domain
        self.params = params or {}

    def to_problem(self):
        """
        Convert config to a QuantumKernel-compatible problem dict.
        """
        return {
            "domain": self.domain,
            "params": self.params
        }


class QuantumProblem:
    """
    A wrapper for problems used by QuantumKernel.solve()
    Included for compatibility with your existing architecture.
    """
    def __init__(self, domain: str, params=None):
        self.domain = domain
        self.params = params or {}

    def to_dict(self):
        return {
            "domain": self.domain,
            "params": self.params
        }
