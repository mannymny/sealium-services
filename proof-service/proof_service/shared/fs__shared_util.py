import re
import hashlib
from pathlib import Path

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\|?*]', '_', name)
    return re.sub(r'\s+', '_', name).strip()

def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def hash_file_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()