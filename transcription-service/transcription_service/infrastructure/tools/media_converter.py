from __future__ import annotations

from pathlib import Path

from ...domain.ports.media_converter_port import MediaConverterPort
from ...shared.fs__shared_util import run


class FfmpegMediaConverter(MediaConverterPort):
    def __init__(self, *, ffmpeg: Path):
        self.ffmpeg = ffmpeg

    def ensure_mp4(self, input_path: Path, out_dir: Path) -> Path:
        if input_path.suffix.lower() == ".mp4":
            return input_path

        mp4_path = out_dir / f"{input_path.stem}.mp4"
        cmd = [
            str(self.ffmpeg),
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", str(input_path),
            "-vn",
            "-c:a", "aac",
            "-b:a", "192k",
            str(mp4_path),
        ]
        run(cmd, check=True)
        return mp4_path
