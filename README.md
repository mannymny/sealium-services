# Sealium Services

Proof Service (FastAPI) to generate evidence packages from URLs or local files.
Transcription Service (FastAPI) to download/transcribe URLs (X Spaces, YouTube, Kick) and return a ZIP with MP4 + PDF + transcript TXT + hashes + manifest.

## Project Layout

```
sealium-services/
  proof-service/
    proof_service/
      application/
      domain/
      infrastructure/
      shared/
      main.py
      settings.py
    tests/
  transcription-service/
    transcription_service/
      application/
      domain/
      infrastructure/
      shared/
      main.py
      settings.py
    tests/
  requirements.txt
  .env
  .env.example
```

## Requirements

- Python 3.10+ (3.12 recommended)
- Playwright browsers (installed once)
- FFmpeg (Linux) or auto-download on Windows for transcription service
- yt-dlp + faster-whisper + reportlab (already in requirements.txt)

## Setup (Windows / Linux)

1) Create and activate a virtual environment:

Windows PowerShell:
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:
```
python -m venv .venv
source .venv/bin/activate
```

2) Install dependencies:
```
python -m pip install -r requirements.txt
```

3) Install Playwright browsers (required for URL captures):
```
python -m playwright install
```

## Environment Variables

Copy `.env.example` to `.env` and edit as needed. Paths can be relative to the repo root.

```
OUTPUT_ROOT=
LOGS_DIR=
TSA_URL=
FORENSIC_USN_SAMPLE_LINES=

CAPTURE_NAV_TIMEOUT_MS=
CAPTURE_WAIT_AFTER_MS=
CAPTURE_WAIT_SELECTOR=
CAPTURE_HEADLESS=

OUTPUT_KEEP_DIR=

# Transcription Service
TRANSCRIPTION_OUTPUT_ROOT=
TRANSCRIPTION_LOGS_DIR=
TRANSCRIPTION_KEEP_DIR=true
TRANSCRIPTION_DEFAULT_LANG=
TRANSCRIPTION_ENGINE=
TRANSCRIPTION_FW_MODEL=
TRANSCRIPTION_FW_DEVICE=
TRANSCRIPTION_FW_COMPUTE=
TRANSCRIPTION_SPONSOR_TEXT=
```

### Proof Service (line by line)
- `OUTPUT_ROOT`: Base folder where proof cases and ZIPs are stored.
- `LOGS_DIR`: Folder for error logs (JSON).
- `TSA_URL`: RFC3161 timestamp authority URL used for proof timestamps.
- `FORENSIC_USN_SAMPLE_LINES`: Max lines of USN journal sampled on Windows for file proofs.
- `CAPTURE_NAV_TIMEOUT_MS`: Playwright navigation timeout in milliseconds.
- `CAPTURE_WAIT_AFTER_MS`: Wait time after page load in milliseconds (stability).
- `CAPTURE_WAIT_SELECTOR`: Selector to wait for before capture (e.g., `article`).
- `CAPTURE_HEADLESS`: `true`/`false` for headless browser.
- `OUTPUT_KEEP_DIR`: If `true`, keep the case folder after zipping. If `false`, only ZIP is kept.

### Transcription Service (line by line)
- `TRANSCRIPTION_OUTPUT_ROOT`: Base folder where transcription cases and ZIPs are stored.
- `TRANSCRIPTION_LOGS_DIR`: Folder for transcription error logs.
- `TRANSCRIPTION_KEEP_DIR`: If `true`, keep the case folder after zipping. If `false`, only ZIP is kept.
- `TRANSCRIPTION_DEFAULT_LANG`: Default transcription language (e.g., `es`).
- `TRANSCRIPTION_ENGINE`: Engine name. Currently supports `faster-whisper`.
- `TRANSCRIPTION_FW_MODEL`: faster-whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`).
- `TRANSCRIPTION_FW_DEVICE`: `cpu` or `cuda` (NVIDIA only).
- `TRANSCRIPTION_FW_COMPUTE`: Compute type (`int8`, `float16`, `float32`).
- `TRANSCRIPTION_SPONSOR_TEXT`: Sponsor line printed at top of PDFs.

## Run the Proof API

From the repo root:

```
$env:PYTHONPATH = ".\proof-service"
python -m proof_service.main
```

Or, using Uvicorn directly:
```
uvicorn proof_service.main:app --reload --app-dir .\proof-service
```

## Run the Transcription API

From the repo root:

```
$env:PYTHONPATH = ".\transcription-service"
python -m transcription_service.main
```

Or, using Uvicorn directly:
```
uvicorn transcription_service.main:app --reload --app-dir .\transcription-service
```

## Proof Endpoints

### Create URL Proof (async job)

```
POST /proof/url
{
  "url": "https://example.com"
}
```

Response:
```
{
  "status": "queued",
  "job_id": "..."
}
```

### Create File Proof (async job)

```
POST /proof/file
{
  "path": "C:/path/to/file.txt",
  "forensic_mode": false
}
```

### Check Job Status

```
GET /proof/status?job_id=...
```

Response when done:
```
{
  "status": "success",
  "type": "url",
  "result": {
    "status": "success",
    "case_id": "...",
    "zip_path": "...",
    "path": "..." // present only when OUTPUT_KEEP_DIR=true
  }
}
```

### Verify Proof (async job)

```
POST /proof/verify
{
  "proof_dir": "C:/path/to/case_folder"
}
```

Response when done:
```
{
  "status": "success",
  "type": "verify",
  "result": {
    "status": "success",
    "errors": 0,
    "report_path": "...",
    "proof_dir": "...",
    "hashes_path": "...",
    "zip_path": "..."
  }
}
```

## Transcription Endpoints

### Create URL Transcription (async job)

```
POST /transcription/url
{
  "url": "https://x.com/i/spaces/ID"
}
```

Optional fields:
```
{
  "url": "...",
  "lang": "es",
  "cookies_from_browser": "chrome"
}
```

### Create File Transcription (async job)

```
POST /transcription/file
{
  "path": "C:/path/to/video.mp4",
  "lang": "es"
}
```

### Check Job Status

```
GET /transcription/status?job_id=...
```

### ZIP Contents (Transcription)

Each transcription job returns a ZIP with:
- The downloaded media in `.mp4` (audio-only MP4)
- Transcript TXT (minute chunks)
- Transcript PDF
- `hashes.sha256`
- `manifest.json`

## Tests

```
cd proof-service
python -m pytest

cd ..\transcription-service
python -m pytest
```
