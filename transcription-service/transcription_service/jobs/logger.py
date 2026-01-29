from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


class JobLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {message}"
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
