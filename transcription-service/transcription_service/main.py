from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .settings import settings
from .jobs.models import JobInput, JobOptions, JobState, JobTimestamps
from .jobs.paths import JobPaths
from .jobs.queue import QUEUE_SPLITTER, enqueue
from .jobs.store import JobStore
from .jobs.utils import storage_root
from .workers.splitter import split_job

app = FastAPI(title="Transcription Service Jobs")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobCreateOptions(BaseModel):
    language: str | None = None
    chunk_mode: Literal["silence", "vad"] | None = None
    max_parallel_chunks: int | None = None
    produce_vtt: bool | None = True
    produce_json: bool | None = True
    produce_pdf: bool | None = True
    cookies_from_browser: str | None = None


class JobCreateInput(BaseModel):
    type: Literal["url", "path", "upload"]
    value: str | None = None


class JobCreateRequest(BaseModel):
    input: JobCreateInput
    options: JobCreateOptions | None = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    status_url: str
    result_url: str


def _build_options(opts: JobCreateOptions | None) -> JobOptions:
    return JobOptions(
        language=(opts.language if opts and opts.language else settings.TRANSCRIPTION_DEFAULT_LANG),
        chunk_mode=(opts.chunk_mode if opts and opts.chunk_mode else settings.CHUNK_MODE),
        max_parallel_chunks=(
            opts.max_parallel_chunks
            if opts and opts.max_parallel_chunks is not None
            else settings.MAX_PARALLEL_CHUNKS
        ),
        produce_vtt=(opts.produce_vtt if opts and opts.produce_vtt is not None else True),
        produce_json=(opts.produce_json if opts and opts.produce_json is not None else True),
        produce_pdf=(opts.produce_pdf if opts and opts.produce_pdf is not None else True),
        cookies_from_browser=(opts.cookies_from_browser if opts else None),
    )


def _parse_multipart_options(raw: str | None) -> JobCreateOptions | None:
    if not raw:
        return None
    data = json.loads(raw)
    return JobCreateOptions.model_validate(data)


@app.post("/v1/transcriptions/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(
    payload: JobCreateRequest | None = Body(None),
    input_type: str | None = Form(None),
    input_value: str | None = Form(None),
    options: str | None = Form(None),
    file: UploadFile | None = File(None),
):
    if payload is None and file is None:
        raise HTTPException(status_code=422, detail="payload or file is required")

    if file is not None:
        input_kind = "upload"
        input_val = file.filename or "upload"
        opts = _parse_multipart_options(options)
    else:
        input_kind = payload.input.type
        input_val = payload.input.value
        opts = payload.options

    if input_kind in {"url", "path"} and not input_val:
        raise HTTPException(status_code=422, detail="input value is required")

    job_id = str(uuid4())
    ts = _now_iso()

    job_input = JobInput(type=input_kind, value=input_val or "")
    job_options = _build_options(opts)

    state = JobState(
        job_id=job_id,
        status="queued",
        timestamps=JobTimestamps(created_at=ts, updated_at=ts),
        input=job_input,
        options=job_options,
    )

    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    store.create(state)

    paths = JobPaths(storage_root(), job_id)
    if file is not None:
        paths.input_dir.mkdir(parents=True, exist_ok=True)
        with paths.original_mp4.open("wb") as f:
            shutil.copyfileobj(file.file, f)

    enqueue(QUEUE_SPLITTER, split_job, job_id)

    return JobCreateResponse(
        job_id=job_id,
        status="queued",
        status_url=f"/v1/transcriptions/jobs/{job_id}",
        result_url=f"/v1/transcriptions/jobs/{job_id}/result",
    )


@app.get("/v1/transcriptions/jobs/{job_id}")
async def get_job(job_id: str):
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    return job.model_dump()


@app.get("/v1/transcriptions/jobs/{job_id}/result")
async def get_result(job_id: str):
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail={"status": job.status})

    return {
        "job_id": job_id,
        "status": job.status,
        "result": job.result.model_dump() if job.result else None,
        "download_url": f"/v1/transcriptions/jobs/{job_id}/download",
    }


@app.get("/v1/transcriptions/jobs/{job_id}/download")
async def download_result(job_id: str):
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail={"status": job.status})
    if not job.result or not job.result.zip_path:
        raise HTTPException(status_code=404, detail="result not found")

    zip_path = Path(job.result.zip_path)
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip not found")

    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


@app.post("/v1/transcriptions/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    if job.status in {"done", "failed", "canceled"}:
        return job.model_dump()
    store.set_status(job_id, "canceled")
    return store.load(job_id).model_dump()
