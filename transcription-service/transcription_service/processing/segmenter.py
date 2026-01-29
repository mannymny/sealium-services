from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..shared.fs__shared_util import run


@dataclass
class Segment:
    index: int
    start: float
    end: float


@dataclass
class SegmenterResult:
    duration: float
    segments: list[Segment]


_SILENCE_START = re.compile(r"silence_start:\s*(\d+(?:\.\d+)?)")
_SILENCE_END = re.compile(r"silence_end:\s*(\d+(?:\.\d+)?)")


def ffprobe_duration_seconds(ffprobe: Path, media_path: Path) -> float:
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
        return float(raw)
    except Exception:
        return 0.0


def parse_silencedetect_output(output: str) -> list[tuple[float, float]]:
    silences: list[tuple[float, float]] = []
    cur_start: float | None = None

    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m_start = _SILENCE_START.search(line)
        if m_start:
            cur_start = float(m_start.group(1))
            continue
        m_end = _SILENCE_END.search(line)
        if m_end and cur_start is not None:
            end = float(m_end.group(1))
            if end > cur_start:
                silences.append((cur_start, end))
            cur_start = None

    return silences


def _split_long_segments(segments: list[tuple[float, float]], max_seconds: int) -> list[tuple[float, float]]:
    if max_seconds <= 0:
        return segments
    result: list[tuple[float, float]] = []
    for start, end in segments:
        cur = start
        while cur < end:
            nxt = min(cur + max_seconds, end)
            result.append((cur, nxt))
            cur = nxt
    return result


def segments_from_silence(silences: list[tuple[float, float]], duration: float, max_chunk_seconds: int) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    cur = 0.0

    for s, e in silences:
        if s > cur:
            segments.append((cur, s))
        cur = max(cur, e)

    if duration > cur:
        segments.append((cur, duration))

    if not segments and duration > 0:
        segments = [(0.0, duration)]

    segments = [(s, e) for s, e in segments if e > s]
    return _split_long_segments(segments, max_chunk_seconds)


def segment_audio_silence(
    *,
    ffmpeg: Path,
    ffprobe: Path,
    audio_path: Path,
    silence_db: str,
    silence_min_duration: float,
    max_chunk_seconds: int,
) -> SegmenterResult:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-i", str(audio_path),
        "-af", f"silencedetect=noise={silence_db}:d={silence_min_duration}",
        "-f", "null",
        "-",
    ]
    res = run(cmd, capture=True, check=False)
    output = (res.stderr or "") + "\n" + (res.stdout or "")
    silences = parse_silencedetect_output(output)
    duration = ffprobe_duration_seconds(ffprobe, audio_path)
    segments_raw = segments_from_silence(silences, duration, max_chunk_seconds)

    segments: list[Segment] = [
        Segment(index=i + 1, start=s, end=e)
        for i, (s, e) in enumerate(segments_raw)
    ]
    return SegmenterResult(duration=duration, segments=segments)


def segment_audio_vad(
    *,
    audio_path: Path,
    vad_model_path: Path,
    vad_threshold: float,
    vad_min_speech_ms: int,
    vad_min_silence_ms: int,
    max_chunk_seconds: int,
) -> SegmenterResult:
    try:
        import torch
        from silero_vad import get_speech_timestamps, read_audio
    except Exception as exc:
        raise RuntimeError("silero-vad and torch are required for CHUNK_MODE=vad") from exc

    if not vad_model_path.exists():
        raise RuntimeError(f"Silero VAD model not found: {vad_model_path}")

    wav = read_audio(str(audio_path), sampling_rate=16000)
    model = torch.jit.load(str(vad_model_path))

    speech_timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=16000,
        threshold=vad_threshold,
        min_speech_duration_ms=vad_min_speech_ms,
        min_silence_duration_ms=vad_min_silence_ms,
        return_seconds=False,
    )

    segments_raw: list[tuple[float, float]] = []
    for item in speech_timestamps:
        start_s = float(item["start"]) / 16000.0
        end_s = float(item["end"]) / 16000.0
        if end_s > start_s:
            segments_raw.append((start_s, end_s))

    if not segments_raw:
        segments_raw = [(0.0, float(len(wav)) / 16000.0)]

    segments_raw = _split_long_segments(segments_raw, max_chunk_seconds)

    segments = [
        Segment(index=i + 1, start=s, end=e)
        for i, (s, e) in enumerate(segments_raw)
    ]
    duration = float(len(wav)) / 16000.0
    return SegmenterResult(duration=duration, segments=segments)


def segment_audio(
    *,
    mode: str,
    ffmpeg: Path,
    ffprobe: Path,
    audio_path: Path,
    silence_db: str,
    silence_min_duration: float,
    max_chunk_seconds: int,
    vad_model_path: Path | None,
    vad_threshold: float,
    vad_min_speech_ms: int,
    vad_min_silence_ms: int,
) -> SegmenterResult:
    if mode == "vad":
        if not vad_model_path:
            raise RuntimeError("SILERO_VAD_MODEL_PATH is required for CHUNK_MODE=vad")
        return segment_audio_vad(
            audio_path=audio_path,
            vad_model_path=vad_model_path,
            vad_threshold=vad_threshold,
            vad_min_speech_ms=vad_min_speech_ms,
            vad_min_silence_ms=vad_min_silence_ms,
            max_chunk_seconds=max_chunk_seconds,
        )

    return segment_audio_silence(
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        audio_path=audio_path,
        silence_db=silence_db,
        silence_min_duration=silence_min_duration,
        max_chunk_seconds=max_chunk_seconds,
    )


def write_segments_json(segments: list[Segment], out_path: Path) -> None:
    payload = [
        {"index": s.index, "start": s.start, "end": s.end}
        for s in segments
    ]
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
