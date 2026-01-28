import json
import platform
from pathlib import Path
from ...domain.ports.capture_port import FileForensicPort


class LinuxForensicAdapter(FileForensicPort):
    async def collect_metadata(self, file_path: str, destination_dir: str) -> None:
        dest = Path(destination_dir)
        info = {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
        }
        with open(dest / "system_basic_info.json", "w") as f:
            json.dump(info, f, indent=2)

    async def collect_system_logs(self, destination_dir: str) -> None:
        # No-op for now; Linux log collection varies by distro.
        dest = Path(destination_dir)
        with open(dest / "eventlog_system_tail.txt", "w") as f:
            f.write("Linux log collection not configured.\n")
