import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class TelemetryStore:
    """
    Simple append-only JSONL telemetry store.

    - One JSON object per line.
    - Best-effort writes (never crash caller).
    - Optional size-based rotation.
    """

    def __init__(self, path: Path, max_bytes: int = 5_000_000) -> None:
        self.path = path
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, snapshot: Dict[str, Any]) -> None:
        """
        Append a single snapshot to the log as compact JSON.

        Failures are swallowed to keep the VQM loop alive.
        """
        try:
            line = json.dumps(snapshot, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # Telemetry is best-effort; never break the main loop.
            return

    def rotate_if_needed(self) -> None:
        """
        If log exceeds max_bytes, rotate it to a timestamped file.

        This is intentionally simple: no compression, no index,
        just "don't let the file grow forever".
        """
        try:
            if not self.path.exists():
                return

            size = self.path.stat().st_size
            if size < self.max_bytes:
                return

            from datetime import datetime

            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            rotated = self.path.with_name(
                f"{self.path.stem}-{ts}{self.path.suffix or ''}"
            )
            self.path.rename(rotated)
        except Exception:
            # Rotation errors shouldn't crash the brain either.
            return

    def iter_recent(self, max_lines: int = 1000) -> Iterable[Dict[str, Any]]:
        """
        Yield up to max_lines most recent snapshots.

        - Skips invalid / corrupt JSON lines.
        - Returns an empty list on any fatal I/O issues.
        """
        if not self.path.exists():
            return []

        try:
            with self.path.open("r", encoding="utf-8") as f:
                lines = f.readlines()[-max_lines:]
        except Exception:
            return []

        snapshots: List[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                snapshots.append(json.loads(line))
            except json.JSONDecodeError:
                # Corrupt line? Ignore it.
                continue
            except Exception:
                continue

        return snapshots
