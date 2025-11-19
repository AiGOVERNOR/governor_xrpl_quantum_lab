from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolDescriptor:
    name: str
    category: str  # e.g. "fee", "liquidity", "pathfinding", "remittance", "escrow"
    version: str = "0.1.0"
    score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    In-memory registry of mesh tools.

    Tools do NOT contain keys or execution power here.
    They simply describe capabilities and performance signals.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDescriptor] = {}

    def register(
        self,
        name: str,
        category: str,
        version: str = "0.1.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolDescriptor:
        desc = ToolDescriptor(
            name=name,
            category=category,
            version=version,
            metadata=metadata or {},
        )
        self._tools[name] = desc
        return desc

    def list_tools(self) -> List[ToolDescriptor]:
        return list(self._tools.values())

    def get(self, name: str) -> Optional[ToolDescriptor]:
        return self._tools.get(name)

    def record_result(self, name: str, delta_score: float) -> None:
        """
        Basic reinforcement: tools that perform well get nudged up,
        tools that perform badly get nudged down.
        """
        tool = self._tools.get(name)
        if tool is None:
            return
        tool.score = max(0.0, min(10.0, tool.score + delta_score))

    def as_dict(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "category": t.category,
                "version": t.version,
                "score": t.score,
                "metadata": t.metadata,
            }
            for t in self._tools.values()
        ]


# A simple global registry instance you can reuse
registry = ToolRegistry()
