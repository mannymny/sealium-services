from __future__ import annotations

import json
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rq import Worker

from ..settings import settings
from ..jobs.paths import JobPaths
from ..jobs.store import JobStore
from ..jobs.logger import JobLogger
from ..jobs.queue import QUEUE_MERGER, QUEUE_TRANSCRIBER, enqueue, get_redis
from ..jobs.utils import storage_root
from ..processing.chunk_transcriber import FasterWhisperChunkTranscriber
from .merger import merge_job


def _load_segments(paths: JobPaths) -> list[dict]:
    if not paths.chunks_meta_path.exists():
        return []
    return json.loads(paths.chunks_meta_path.read_text(encoding="utf-8"))


def _write_partial(paths: JobPaths, index: int, payload: dict) -> None:
    paths.partials_dir.mkdir(parents=True, exist_ok=True)
    out_path = paths.partial_path(index)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def transcribe_job(job_id: str) -> None:
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        return
    if job.status == "canceled":
        return

    paths = JobPaths(storage_root(), job_id)
    logger = JobLogger(paths.logs_dir / "job.log")

    try:
        store.set_status(job_id, "transcribing")

        segments = _load_segments(paths)
        total = len(segments)
        done = len(list(paths.partials_dir.glob("*.json"))) if paths.partials_dir.exists() else 0
        store.set_progress(job_id, chunks_total=total, chunks_done=done)

        missing = [seg for seg in segments if not paths.partial_path(int(seg["index"])).exists()]
        if not missing:
            enqueue(QUEUE_MERGER, merge_job, job_id)
            return

        max_parallel = int(job.options.max_parallel_chunks or settings.MAX_PARALLEL_CHUNKS)
        if max_parallel < 1:
            max_parallel = settings.MAX_PARALLEL_CHUNKS

        transcriber = FasterWhisperChunkTranscriber(
            model_size=settings.TRANSCRIPTION_FW_MODEL,
            device=settings.TRANSCRIPTION_FW_DEVICE,
            compute_type=settings.TRANSCRIPTION_FW_COMPUTE,
            beam_size=settings.TRANSCRIPTION_FW_BEAM_SIZE,
            vad_filter=settings.TRANSCRIPTION_FW_VAD_FILTER,
        )

        def _process(seg: dict) -> dict:
            idx = int(seg["index"])
            start = float(seg["start"])
            end = float(seg["end"])
            chunk_path = paths.chunk_path(idx)
            if not chunk_path.exists():
                raise RuntimeError(f"chunk not found: {chunk_path}")
            result = transcriber.transcribe_chunk(chunk_path, chunk_start=start, language=job.options.language)
            payload = {
                "chunk_index": idx,
                "chunk_start": start,
                "chunk_end": end,
                "segments": result.get("segments", []),
                "text": result.get("text", ""),
            }
            _write_partial(paths, idx, payload)
            return payload

        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            futures = {executor.submit(_process, seg): seg for seg in missing}
            for future in as_completed(futures):
                if store.load(job_id).status == "canceled":
                    return
                try:
                    future.result()
                except Exception as exc:
                    store.add_error(job_id, str(exc))
                    raise
                else:
                    done += 1
                    store.set_progress(job_id, chunks_done=done)

        enqueue(QUEUE_MERGER, merge_job, job_id)
        logger.write("transcriber completed")
    except Exception as exc:
        store.add_error(job_id, str(exc))
        store.set_status(job_id, "failed")
        logger.write(traceback.format_exc())
        raise


def main() -> None:
    worker = Worker([QUEUE_TRANSCRIBER], connection=get_redis())
    worker.work()


if __name__ == "__main__":
    main()
