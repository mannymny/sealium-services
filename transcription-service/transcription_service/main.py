import asyncio
import uvicorn
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .settings import settings
from .infrastructure.monitoring.json_monitor_adapter import JsonErrorMonitorAdapter
from .infrastructure.packaging.zip_packager import ZipPackagerAdapter
from .infrastructure.pdf.reportlab_adapter import ReportLabPdfWriterAdapter
from .infrastructure.tools.ffmpeg_provider import ensure_ffmpeg
from .infrastructure.tools.media_converter import FfmpegMediaConverter
from .infrastructure.downloader.yt_dlp_adapter import YtDlpDownloaderAdapter
from .infrastructure.transcriber.faster_whisper_adapter import FasterWhisperTranscriberAdapter
from .application.use_cases.create_url_transcription import CreateUrlTranscriptionUseCase
from .application.use_cases.create_file_transcription import CreateFileTranscriptionUseCase

app = FastAPI(title="Transcription Service DDD")

BASE_DIR = Path(__file__).resolve().parents[2]
logs_dir = Path(settings.TRANSCRIPTION_LOGS_DIR)
output_root = Path(settings.TRANSCRIPTION_OUTPUT_ROOT)
if not logs_dir.is_absolute():
    logs_dir = BASE_DIR / logs_dir
if not output_root.is_absolute():
    output_root = BASE_DIR / output_root

tools_dir = BASE_DIR / "transcription-service" / ".tools"

monitor = JsonErrorMonitorAdapter(str(logs_dir / "transcription_errors.json"))
packager = ZipPackagerAdapter()
pdf_writer = ReportLabPdfWriterAdapter()

ffmpeg, ffprobe = ensure_ffmpeg(tools_dir)
converter = FfmpegMediaConverter(ffmpeg=ffmpeg)

transcriber = FasterWhisperTranscriberAdapter(
    ffmpeg=ffmpeg,
    ffprobe=ffprobe,
    model_size=settings.TRANSCRIPTION_FW_MODEL,
    device=settings.TRANSCRIPTION_FW_DEVICE,
    compute_type=settings.TRANSCRIPTION_FW_COMPUTE,
)

downloader = YtDlpDownloaderAdapter(ffmpeg=ffmpeg)

uc_url = CreateUrlTranscriptionUseCase(
    downloader,
    transcriber,
    pdf_writer,
    packager,
    monitor,
    str(output_root),
    keep_dir=settings.TRANSCRIPTION_KEEP_DIR,
    sponsor_text=settings.TRANSCRIPTION_SPONSOR_TEXT,
)

uc_file = CreateFileTranscriptionUseCase(
    transcriber,
    pdf_writer,
    packager,
    converter,
    monitor,
    str(output_root),
    keep_dir=settings.TRANSCRIPTION_KEEP_DIR,
    sponsor_text=settings.TRANSCRIPTION_SPONSOR_TEXT,
)

jobs = {}


async def _run_url_job(job_id: str, url: str, lang: str, cookies_from_browser: str | None) -> None:
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        result = await uc_url.execute(url, lang=lang, cookies_from_browser=cookies_from_browser)
        jobs[job_id]["status"] = "success"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        jobs[job_id]["finished_at_utc"] = datetime.now(timezone.utc).isoformat()


async def _run_file_job(job_id: str, path: str, lang: str) -> None:
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        result = await uc_file.execute(path, lang=lang)
        jobs[job_id]["status"] = "success"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        jobs[job_id]["finished_at_utc"] = datetime.now(timezone.utc).isoformat()


class UrlReq(BaseModel):
    url: str
    lang: str | None = None
    cookies_from_browser: str | None = None


class FileReq(BaseModel):
    path: str
    lang: str | None = None


@app.post("/transcription/url")
async def create_url_transcription(req: UrlReq):
    job_id = str(uuid4())
    jobs[job_id] = {"status": "queued", "type": "url", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    lang = req.lang or settings.TRANSCRIPTION_DEFAULT_LANG
    asyncio.create_task(_run_url_job(job_id, req.url, lang, req.cookies_from_browser))
    return {"status": "queued", "job_id": job_id}


@app.post("/transcription/file")
async def create_file_transcription(req: FileReq):
    job_id = str(uuid4())
    jobs[job_id] = {"status": "queued", "type": "file", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    lang = req.lang or settings.TRANSCRIPTION_DEFAULT_LANG
    asyncio.create_task(_run_file_job(job_id, req.path, lang))
    return {"status": "queued", "job_id": job_id}


@app.get("/transcription/status")
async def get_job_status(job_id: str = Query(..., description="Job ID to query")):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    return job


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
