from __future__ import annotations

import json
import shutil
import traceback
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from rq import Worker

from ..settings import settings
from ..jobs.paths import JobPaths
from ..jobs.store import JobStore
from ..jobs.logger import JobLogger
from ..jobs.queue import QUEUE_TRANSCRIBER, enqueue, get_redis
from ..jobs.utils import storage_root
from ..processing.segmenter import segment_audio, write_segments_json
from ..shared.fs__shared_util import ensure_directory, run
from ..infrastructure.tools.ffmpeg_provider import ensure_ffmpeg
from ..infrastructure.downloader.yt_dlp_adapter import YtDlpDownloaderAdapter
from .transcriber import transcribe_job


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _download_direct(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def _ensure_original(job, paths: JobPaths, logger: JobLogger, ffmpeg: Path) -> None:
    if paths.original_mp4.exists():
        return

    input_type = job.input.type
    input_value = job.input.value

    if input_type == "upload":
        if not paths.original_mp4.exists():
            raise RuntimeError("uploaded file is missing")
        return

    if input_type == "path":
        src = Path(input_value)
        if not src.exists():
            raise RuntimeError(f"input path not found: {src}")
        ensure_directory(paths.input_dir)
        shutil.copy2(src, paths.original_mp4)
        return

    if input_type == "url":
        parsed = urlparse(input_value)
        if parsed.scheme in {"http", "https"} and parsed.path.lower().endswith(".mp4"):
            logger.write("downloading direct mp4")
            _download_direct(input_value, paths.original_mp4)
            return

        downloader = YtDlpDownloaderAdapter(ffmpeg=ffmpeg)
        logger.write("downloading via yt-dlp")
        media_path = downloader.download(input_value, paths.input_dir, cookies_from_browser=job.options.cookies_from_browser)
        if not media_path.exists():
            raise RuntimeError("downloaded media not found")
        shutil.copy2(media_path, paths.original_mp4)
        return

    raise RuntimeError(f"unsupported input type: {input_type}")


def _normalize_audio(ffmpeg: Path, paths: JobPaths, logger: JobLogger) -> None:
    if paths.audio_wav.exists():
        return
    if not paths.original_mp4.exists():
        raise RuntimeError("original.mp4 not found")

    ensure_directory(paths.input_dir)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(paths.original_mp4),
        "-ac", "1",
        "-ar", "16000",
        "-vn",
        "-c:a", "pcm_s16le",
        str(paths.audio_wav),
    ]
    logger.write("normalizing audio")
    run(cmd, check=True)


def _export_chunk(ffmpeg: Path, audio_path: Path, chunk_path: Path, start: float, end: float) -> None:
    duration = max(end - start, 0.01)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(audio_path),
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(chunk_path),
    ]
    run(cmd, check=True)


def split_job(job_id: str) -> None:
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        return
    if job.status == "canceled":
        return

    paths = JobPaths(storage_root(), job_id)
    logger = JobLogger(paths.logs_dir / "job.log")

    try:
        store.set_status(job_id, "splitting")
        ffmpeg, ffprobe = ensure_ffmpeg(Path(__file__).resolve().parents[3] / "transcription-service" / ".tools")

        _ensure_original(job, paths, logger, ffmpeg)
        _normalize_audio(ffmpeg, paths, logger)

        if paths.chunks_meta_path.exists():
            segments_data = json.loads(paths.chunks_meta_path.read_text(encoding="utf-8"))
        else:
            result = segment_audio(
                mode=job.options.chunk_mode,
                ffmpeg=ffmpeg,
                ffprobe=ffprobe,
                audio_path=paths.audio_wav,
                silence_db=settings.SILENCE_DB,
                silence_min_duration=settings.SILENCE_MIN_DURATION,
                max_chunk_seconds=settings.MAX_CHUNK_SECONDS,
                vad_model_path=Path(settings.SILERO_VAD_MODEL_PATH) if settings.SILERO_VAD_MODEL_PATH else None,
                vad_threshold=settings.VAD_THRESHOLD,
                vad_min_speech_ms=settings.VAD_MIN_SPEECH_MS,
                vad_min_silence_ms=settings.VAD_MIN_SILENCE_MS,
            )
            ensure_directory(paths.chunks_dir)
            write_segments_json(result.segments, paths.chunks_meta_path)
            segments_data = [
                {"index": s.index, "start": s.start, "end": s.end}
                for s in result.segments
            ]

        segments = segments_data or []
        ensure_directory(paths.chunks_dir)
        for seg in segments:
            if store.load(job_id).status == "canceled":
                return
            idx = int(seg["index"])
            start = float(seg["start"])
            end = float(seg["end"])
            chunk_path = paths.chunk_path(idx)
            if chunk_path.exists():
                continue
            _export_chunk(ffmpeg, paths.audio_wav, chunk_path, start, end)

        store.set_progress(job_id, chunks_total=len(segments))
        enqueue(QUEUE_TRANSCRIBER, transcribe_job, job_id)
        logger.write("splitter completed")
    except Exception as exc:
        store.add_error(job_id, str(exc))
        store.set_status(job_id, "failed")
        logger.write(traceback.format_exc())
        raise


def main() -> None:
    worker = Worker([QUEUE_SPLITTER], connection=get_redis())
    worker.work()


if __name__ == "__main__":
    main()
