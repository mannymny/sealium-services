# Sealium Services

Proof Service (FastAPI) to generate evidence packages from URLs or local files.

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
  requirements.txt
  .env
  .env.example
```

## Requirements

- Python 3.10+ (3.12 recommended)
- Playwright browsers (installed once)

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

Copy `.env.example` to `.env` and edit as needed.

```
OUTPUT_ROOT=./proof_output
LOGS_DIR=./logs
TSA_URL=http://timestamp.sectigo.com/rfc3161
FORENSIC_USN_SAMPLE_LINES=6000

CAPTURE_NAV_TIMEOUT_MS=120000
CAPTURE_WAIT_AFTER_MS=8000
CAPTURE_WAIT_SELECTOR=article
CAPTURE_HEADLESS=true

OUTPUT_KEEP_DIR=true
```

Notes:
- `OUTPUT_KEEP_DIR=false` makes the service keep only the ZIP (it deletes the case folder after zipping).
- `CAPTURE_HEADLESS=false` can help with sites that block headless browsers.

## Run the API

From the repo root:

```
$env:PYTHONPATH = ".\proof-service"
python -m proof_service.main
```

Or, using Uvicorn directly:
```
uvicorn proof_service.main:app --reload --app-dir .\proof-service
```

## Endpoints

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
GET /proof/status/{job_id}
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

## Output Naming

For X/Twitter URLs:
```
YYYYMMDD_HHMMSS_username_tweetId
```

Otherwise:
```
YYYYMMDD_HHMMSS_host
```

The ZIP uses the same name. When `OUTPUT_KEEP_DIR=true`, the folder uses the same name as well.

## Output Files

Each URL case includes:
- `page_screenshot.png` (full-page capture)
- `page_print.pdf` (generated from the screenshot)
- `page.html` (self-contained HTML with embedded screenshot)
- `manifest.json`, `hashes.sha256`, `timestamps/`, and other metadata

Notes:
- MHTML is not generated.
- HTML/PDF are derived from the screenshot to ensure visual fidelity.

## Linux Notes

- URL capture works on Linux; you still must run `playwright install`.
- File forensics are implemented as a no-op on Linux (placeholder). Windows uses `fsutil` and `wevtutil`.

## Tests

```
cd proof-service
python -m pytest
```
