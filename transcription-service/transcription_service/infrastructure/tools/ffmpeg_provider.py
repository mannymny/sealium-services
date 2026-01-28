from __future__ import annotations

import os
import platform
import shutil
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

from ...shared.fs__shared_util import ensure_directory, is_windows, which


def _http_download(url: str, out: Path) -> None:
    ensure_directory(out.parent)
    headers = {"User-Agent": "transcription-service", "Accept": "*/*"}
    req = Request(url, headers=headers)
    with urlopen(req) as r, open(out, "wb") as f:
        shutil.copyfileobj(r, f)


def _test_zip(zip_path: Path) -> bool:
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            return z.testzip() is None
    except Exception:
        return False


def _extract_zip(zip_path: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    ensure_directory(dest)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)


def ensure_ffmpeg(tools_dir: Path) -> tuple[Path, Path]:
    ffmpeg = which("ffmpeg")
    ffprobe = which("ffprobe")
    if ffmpeg and ffprobe:
        return Path(ffmpeg), Path(ffprobe)

    ensure_directory(tools_dir)

    if not is_windows():
        raise RuntimeError(
            "Could not find ffmpeg/ffprobe in PATH. Install FFmpeg on Linux and try again."
        )

    arch = platform.machine().lower()
    if "64" not in arch and "amd64" not in arch and "x86_64" not in arch:
        raise RuntimeError(f"Unsupported architecture for auto-download: {platform.machine()}")

    zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = tools_dir / "ffmpeg-release-essentials.zip"
    ff_dir = tools_dir / "ffmpeg"

    if zip_path.exists():
        zip_path.unlink(missing_ok=True)

    _http_download(zip_url, zip_path)

    if zip_path.stat().st_size < 500_000 or not _test_zip(zip_path):
        raise RuntimeError("FFmpeg ZIP looks invalid (too small or corrupted).")

    _extract_zip(zip_path, ff_dir)

    bin_dir = None
    for p in ff_dir.rglob("bin"):
        if (p / "ffmpeg.exe").exists() and (p / "ffprobe.exe").exists():
            bin_dir = p
            break
    if not bin_dir:
        raise RuntimeError("Could not locate ffmpeg.exe/ffprobe.exe inside the extracted ZIP.")

    os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
    return bin_dir / "ffmpeg.exe", bin_dir / "ffprobe.exe"
