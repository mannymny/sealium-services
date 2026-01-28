from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from ...domain.ports.downloader_port import DownloaderPort
from ...domain.ports.bulk_downloader_port import BulkDownloaderPort
from ...shared.fs__shared_util import ensure_directory, run, safe_path_component, which


class YtDlpDownloaderAdapter(DownloaderPort, BulkDownloaderPort):
    def __init__(self, *, ffmpeg: Path):
        self.ffmpeg = ffmpeg

    def _extract_space_id(self, url: str) -> str:
        m = re.search(r"/i/spaces/([A-Za-z0-9]+)", url or "")
        return m.group(1) if m else "unknown"

    def _yt_dlp_get_title(self, url: str, *, cookies_from_browser: str | None = None) -> str:
        ytdlp = which("yt-dlp")
        if not ytdlp:
            raise RuntimeError("yt-dlp not found. Install: pip install -U yt-dlp")

        cmd = [ytdlp, "-J", "--no-playlist", url]
        if cookies_from_browser:
            cmd.extend(["--cookies-from-browser", cookies_from_browser])

        res = run(cmd, capture=True, check=True)
        data = json.loads(res.stdout or "{}")

        title = data.get("title") or ""
        if not title:
            entries = data.get("entries") or []
            if entries and isinstance(entries, list) and isinstance(entries[0], dict):
                title = entries[0].get("title") or ""

        return title or "Media"

    def _ensure_mp4(self, media_path: Path, out_dir: Path) -> Path:
        if media_path.suffix.lower() == ".mp4":
            return media_path

        mp4_path = out_dir / f"{media_path.stem}.mp4"
        cmd = [
            str(self.ffmpeg),
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(media_path),
            "-vn",
            "-c:a", "aac",
            "-b:a", "192k",
            str(mp4_path),
        ]
        run(cmd, check=True)
        return mp4_path

    def download(self, url: str, out_dir: Path, *, cookies_from_browser: str | None = None) -> Path:
        ytdlp = which("yt-dlp")
        if not ytdlp:
            raise RuntimeError("yt-dlp not found. Install: pip install -U yt-dlp")

        ensure_directory(out_dir)

        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        space_id = self._extract_space_id(url)
        raw_title = self._yt_dlp_get_title(url, cookies_from_browser=cookies_from_browser)
        safe_title = safe_path_component(raw_title, max_len=60)
        safe_sid = safe_path_component(space_id, max_len=20)
        folder_name = safe_path_component(f"{ts_str}_{safe_title}_SpaceID_{safe_sid}", max_len=120)
        item_dir = ensure_directory(out_dir / folder_name)

        outtmpl = "%(title).80B_%(id)s.%(ext)s"
        cmd = [
            ytdlp,
            "--no-playlist",
            "-N",
            "8",
            "--concurrent-fragments",
            "8",
            "-f",
            "bv*+ba/best",
            "--merge-output-format",
            "mp4",
            "--restrict-filenames",
            "-o",
            outtmpl,
            url,
        ]
        if cookies_from_browser:
            cmd.extend(["--cookies-from-browser", cookies_from_browser])

        run(cmd, check=True, cwd=item_dir)

        media_files = list(item_dir.glob("*.mp4"))
        if not media_files:
            exts = (".m4a", ".mp3", ".webm", ".aac", ".wav")
            for ext in exts:
                media_files.extend(item_dir.glob(f"*{ext}"))

        if not media_files:
            raise RuntimeError(f"Media not found in {item_dir}")

        media_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        media_path = media_files[0]
        return self._ensure_mp4(media_path, item_dir)

    def download_all_audio(
        self,
        url: str,
        input_dir: Path,
        *,
        audio_format: str,
        cookies_from_browser: str | None = None,
    ) -> None:
        ytdlp = which("yt-dlp")
        if not ytdlp:
            raise RuntimeError("yt-dlp not found. Install: pip install -U yt-dlp")

        ensure_directory(input_dir)

        archive = input_dir / "ytdlp_archive.txt"
        outtmpl = "%(uploader).40B/%(upload_date>%Y-%m-%d)s - %(title).80B_%(id)s.%(ext)s"

        cmd = [
            ytdlp,
            "-N", "8",
            "--concurrent-fragments", "8",
            "--yes-playlist",
            "--ignore-errors",
            "--download-archive", str(archive),
            "-x",
            "--audio-format", audio_format,
            "--audio-quality", "0",
            "--restrict-filenames",
            "-o", outtmpl,
            url,
        ]
        if cookies_from_browser:
            cmd.extend(["--cookies-from-browser", cookies_from_browser])

        run(cmd, check=True, cwd=input_dir)
