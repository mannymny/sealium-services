import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .settings import settings
from .infrastructure.capture.playwright_adapter import PlaywrightAdapter
from .infrastructure.forensics.windows_adapter import WindowsForensicAdapter
from .infrastructure.tsa.rfc3161_adapter import Rfc3161Adapter
from .infrastructure.monitoring.json_monitor_adapter import JsonErrorMonitorAdapter
from .application.use_cases.create_url_proof import CreateUrlProofUseCase
from .application.use_cases.create_file_proof import CreateFileProofUseCase

app = FastAPI(title="Proof Service DDD")

# Dependency Injection (Wiring)
monitor = JsonErrorMonitorAdapter(f"{settings.LOGS_DIR}/errors.json")
tsa = Rfc3161Adapter(settings.TSA_URL)
url_cap = PlaywrightAdapter()
file_for = WindowsForensicAdapter()

uc_url = CreateUrlProofUseCase(url_cap, tsa, monitor, settings.OUTPUT_ROOT)
uc_file = CreateFileProofUseCase(file_for, tsa, monitor, settings.OUTPUT_ROOT)

class UrlReq(BaseModel):
    url: str

class FileReq(BaseModel):
    path: str
    forensic_mode: bool = False

@app.post("/proof/url")
async def create_url_proof(req: UrlReq):
    try: return await uc_url.execute(req.url)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/proof/file")
async def create_file_proof(req: FileReq):
    try: return await uc_file.execute(req.path, req.forensic_mode)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)