import asyncio
import platform
import uvicorn
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .settings import settings
from .infrastructure.capture.playwright_adapter import PlaywrightAdapter
from .infrastructure.forensics.linux_adapter import LinuxForensicAdapter
from .infrastructure.forensics.windows_adapter import WindowsForensicAdapter
from .infrastructure.tsa.rfc3161_adapter import Rfc3161Adapter
from .infrastructure.monitoring.json_monitor_adapter import JsonErrorMonitorAdapter
from .application.use_cases.create_url_proof import CreateUrlProofUseCase
from .application.use_cases.create_file_proof import CreateFileProofUseCase

app = FastAPI(title="Proof Service DDD")

# Normalize relative paths against the repo root (where .env lives).
BASE_DIR = Path(__file__).resolve().parents[2]
logs_dir = Path(settings.LOGS_DIR)
output_root = Path(settings.OUTPUT_ROOT)
if not logs_dir.is_absolute():
    logs_dir = BASE_DIR / logs_dir
if not output_root.is_absolute():
    output_root = BASE_DIR / output_root

monitor = JsonErrorMonitorAdapter(str(logs_dir / "errors.json"))
tsa = Rfc3161Adapter(settings.TSA_URL)
url_cap = PlaywrightAdapter(
    nav_timeout_ms=settings.CAPTURE_NAV_TIMEOUT_MS,
    wait_after_ms=settings.CAPTURE_WAIT_AFTER_MS,
    wait_selector=settings.CAPTURE_WAIT_SELECTOR,
    headless=settings.CAPTURE_HEADLESS,
)
if platform.system() == "Windows":
    file_for = WindowsForensicAdapter()
else:
    file_for = LinuxForensicAdapter()

uc_url = CreateUrlProofUseCase(url_cap, tsa, monitor, str(output_root), settings.OUTPUT_KEEP_DIR)
uc_file = CreateFileProofUseCase(file_for, tsa, monitor, str(output_root), settings.OUTPUT_KEEP_DIR)

# In-memory job store; jobs are lost on restart.
jobs = {}

async def _run_url_job(job_id: str, url: str) -> None:
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        result = await uc_url.execute(url)
        jobs[job_id]["status"] = "success"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        jobs[job_id]["finished_at_utc"] = datetime.now(timezone.utc).isoformat()

async def _run_file_job(job_id: str, path: str, forensic_mode: bool) -> None:
    jobs[job_id]["status"] = "running"
    jobs[job_id]["started_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        result = await uc_file.execute(path, forensic_mode)
        jobs[job_id]["status"] = "success"
        jobs[job_id]["result"] = result
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        jobs[job_id]["finished_at_utc"] = datetime.now(timezone.utc).isoformat()

class UrlReq(BaseModel):
    url: str

class FileReq(BaseModel):
    path: str
    forensic_mode: bool = False

@app.post("/proof/url")
async def create_url_proof(req: UrlReq):
    job_id = str(uuid4())
    jobs[job_id] = {"status": "queued", "type": "url", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    asyncio.create_task(_run_url_job(job_id, req.url))
    return {"status": "queued", "job_id": job_id}

@app.post("/proof/file")
async def create_file_proof(req: FileReq):
    job_id = str(uuid4())
    jobs[job_id] = {"status": "queued", "type": "file", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    asyncio.create_task(_run_file_job(job_id, req.path, req.forensic_mode))
    return {"status": "queued", "job_id": job_id}

@app.get("/proof/status/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_id not found")
    return job

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
