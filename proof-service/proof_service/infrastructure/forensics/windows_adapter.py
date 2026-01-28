import subprocess
import platform
import json
from pathlib import Path
from ...domain.ports.capture_port import FileForensicPort

class WindowsForensicAdapter(FileForensicPort):
    def _run_cmd(self, cmd: list, output_file: Path):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout + "\n" + result.stderr)
        except Exception as e:
            with open(output_file, "w", encoding="utf-8") as f: f.write(str(e))

    async def collect_metadata(self, file_path: str, destination_dir: str) -> None:
        dest = Path(destination_dir)
        info = {"system": platform.system(), "node": platform.node(), "release": platform.release()}
        with open(dest / "system_basic_info.json", "w") as f: json.dump(info, f, indent=2)
        
        if platform.system() == "Windows":
            self._run_cmd(["fsutil", "file", "queryfileid", file_path], dest / "ntfs_fileid.txt")

    async def collect_system_logs(self, destination_dir: str) -> None:
        if platform.system() == "Windows":
            cmd = ["wevtutil", "qe", "System", "/c:500", "/f:text", "/rd:true"]
            self._run_cmd(cmd, Path(destination_dir) / "eventlog_system_tail.txt")