from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ...domain.ports.transcriber_port import TranscriptionResult, TranscriberPort
from ...shared.fs__shared_util import ensure_directory, remove_diacritics_to_ascii, run, safe_path_component


def ffprobe_duration_seconds(ffprobe: Path, media_path: Path) -> int:
    res = run(
        [
            str(ffprobe),
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture=True,
        check=False,
    )
    raw = (res.stdout or "").strip()
    try:
        return int(round(float(raw)))
    except Exception:
        return 0


def fmt_hhmmss(sec: int) -> str:
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_mmss(sec: int) -> str:
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"


class FasterWhisperTranscriberAdapter(TranscriberPort):
    def __init__(
        self,
        *,
        ffmpeg: Path,
        ffprobe: Path,
        model_size: str,
        device: str,
        compute_type: str,
    ):
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(self, media_path: Path, out_dir: Path, *, lang: str) -> TranscriptionResult:
        from faster_whisper import WhisperModel  # delayed import

        ensure_directory(out_dir)

        duration = ffprobe_duration_seconds(self.ffprobe, media_path)
        if duration <= 0:
            duration = 1

        total_min = (duration + 59) // 60
        total_mmss = fmt_mmss(duration)

        safe_stem = safe_path_component(media_path.stem, max_len=120)
        out_txt = out_dir / f"{safe_stem}.txt"

        tmp_dir = Path(tempfile.mkdtemp(prefix="transcription-fw-"))
        wav_path = tmp_dir / "in.wav"

        try:
            run(
                [
                    str(self.ffmpeg),
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-i", str(media_path),
                    "-vn",
                    "-ac", "1",
                    "-ar", "16000",
                    "-c:a", "pcm_s16le",
                    str(wav_path),
                ],
                check=True,
            )

            model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

            buf_by_minute: dict[int, str] = {}

            segments, _info = model.transcribe(
                str(wav_path),
                language=lang,
                vad_filter=True,
            )

            for seg in segments:
                end_s = float(getattr(seg, "end", 0.0) or 0.0)
                minute = int(end_s) // 60
                text = remove_diacritics_to_ascii(getattr(seg, "text", "") or "")
                if text:
                    buf_by_minute[minute] = (buf_by_minute.get(minute, "") + " " + text).strip()

            lines: list[str] = [f"Duration: {total_mmss}", ""]
            for m in range(total_min):
                a = fmt_hhmmss(m * 60)
                b = fmt_hhmmss((m + 1) * 60)
                txt = (buf_by_minute.get(m, "").strip() or "(no text)")
                txt = remove_diacritics_to_ascii(txt)
                lines.append(f"[{a}] -> [{b}] {txt}")
                lines.append("")

            full_text = remove_diacritics_to_ascii(" ".join(buf_by_minute.get(i, "") for i in range(total_min)))
            out_txt.write_text("\n".join(lines), encoding="utf-8", errors="ignore")

            return TranscriptionResult(txt_path=out_txt, lines=lines, full_text=full_text, duration_sec=duration)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
