from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

_WIN_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_WIN_TRAILING = re.compile(r"[ .]+$")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def hash_file_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def remove_diacritics_to_ascii(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    s = "".join(ch for ch in s if 32 <= ord(ch) <= 126)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_path_component(name: str, *, max_len: int = 80) -> str:
    name = remove_diacritics_to_ascii(name or "")
    name = _WIN_BAD.sub("_", name)
    name = _WIN_TRAILING.sub("", name).strip()

    if not name:
        name = "item"

    if len(name) > max_len:
        name = name[:max_len].rstrip("_- .")
        if not name:
            name = "item"

    return name


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def is_windows() -> bool:
    return os.name == "nt"


def run(cmd: list[str], *, check: bool = True, capture: bool = False, cwd: Path | None = None):
    if capture:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)
