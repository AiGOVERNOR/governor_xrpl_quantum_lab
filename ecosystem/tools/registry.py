import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolScore:
    """
    Represents a single tool's "confidence" score in the ecosystem.

    This is not a magic RL agent, just a bounded scalar that can be
    nudged up/down over time based on outcomes.
    """

    name: str
    score: float = 1.0
    category: str = "generic"
    metadata: Dict[str, Any] = None


class ToolRegistry:
    """
    Persistent registry of tools and their scores.

    - Scores are bounded between [min_score, max_score].
    - A small decay is applied every cycle so recent outcomes matter more.
    - For now, update_from_guardian() just applies decay; later you can
      plug in real "episode outcome" logic.
    """

    def __init__(
        self,
        scores: Dict[str, ToolScore],
        min_score: float = 0.5,
        max_score: float = 3.0,
        decay: float = 0.999,
    ) -> None:
        self.scores = scores
        self.min_score = min_score
        self.max_score = max_score
        self.decay = decay
        self._path: Optional[Path] = None

    # ---------- Persistence helpers ----------

    @classmethod
    def load(cls, path: Path) -> "ToolRegistry":
        if not path.exists():
            return cls(scores={})

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return cls(scores={})

        cfg = raw.get("config", {}) or {}
        score_raw = raw.get("scores", {}) or {}

        scores: Dict[str, ToolScore] = {}
        for name, data in score_raw.items():
            scores[name] = ToolScore(
                name=name,
                score=float(data.get("score", 1.0)),
                category=str(data.get("category", "generic")),
                metadata=data.get("metadata") or {},
            )

        return cls(
            scores=scores,
            min_score=float(cfg.get("min_score", 0.5)),
            max_score=float(cfg.get("max_score", 3.0)),
            decay=float(cfg.get("decay", 0.999)),
        )

    @classmethod
    def load_default(cls, base_dir: Path) -> "ToolRegistry":
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / "tool_registry.json"
        reg = cls.load(path)
        reg._path = path
        return reg

    def save(self) -> None:
        if self._path is None:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "config": {
                "min_score": self.min_score,
                "max_score": self.max_score,
                "decay": self.decay,
            },
            "scores": {
                name: {
                    "score": ts.score,
                    "category": ts.category,
                    "metadata": ts.metadata or {},
                }
                for name, ts in self.scores.items()
            },
        }

        try:
            self._path.write_text(
                json.dumps(data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            # Registry failures shouldn't crash the orchestrator.
            return

    # ---------- Core operations ----------

    def ensure_tool(
        self,
        name: str,
        category: str = "generic",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolScore:
        if name not in self.scores:
            self.scores[name] = ToolScore(
                name=name,
                score=1.0,
                category=category,
                metadata=metadata or {},
            )
        else:
            # Optionally refresh metadata/category
            ts = self.scores[name]
            if metadata:
                ts.metadata = {**(ts.metadata or {}), **metadata}
            ts.category = category or ts.category
        return self.scores[name]

    def decay_scores(self) -> None:
        for ts in self.scores.values():
            ts.score = max(self.min_score, ts.score * self.decay)

    def update_from_guardian(self, guardian_state: Dict[str, Any]) -> None:
        """
        Placeholder intelligence hook:

        For now:
        - Always apply decay (so scores slowly relax toward min_score).
        - Later you can add:
          * reward/penalty based on how quickly fee-pressure episodes resolve,
          * whether a given tool's advice was adopted, etc.
        """
        _ = guardian_state  # reserved for future use
        self.decay_scores()

    def as_export(self) -> List[Dict[str, Any]]:
        """
        Flatten registry into a JSON-friendly list for inclusion
        in the VQM state.
        """
        export: List[Dict[str, Any]] = []
        for ts in self.scores.values():
            export.append(
                {
                    "name": ts.name,
                    "score": ts.score,
                    "category": ts.category,
                    "metadata": ts.metadata or {},
                }
            )
        return export
