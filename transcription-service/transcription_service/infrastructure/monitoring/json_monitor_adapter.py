from __future__ import annotations

import json
import aiofiles
from pathlib import Path
from ...domain.ports.error_monitor_port import ErrorMonitorPort
from ...domain.entities.error_log import ErrorLog


class JsonErrorMonitorAdapter(ErrorMonitorPort):
    def __init__(self, log_path: str):
        self.path = Path(log_path)
        self._ensure_store()

    def _ensure_store(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with open(self.path, "w") as f:
                json.dump([], f)

    async def log_error(self, error: ErrorLog) -> None:
        try:
            self._ensure_store()
            data = error.model_dump()
            data["timestamp_utc"] = error.timestamp_utc.isoformat()
            async with aiofiles.open(self.path, "r") as f:
                content = await f.read()
                logs = json.loads(content) if content else []
            logs.append(data)
            async with aiofiles.open(self.path, "w") as f:
                await f.write(json.dumps(logs, indent=2))
        except Exception as e:
            print(f"Fallback Log Error: {e}")
