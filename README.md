# Sealium Services

Proof Service (FastAPI) generates evidence packages from URLs or local files.
Transcription Service (FastAPI) runs a job-based pipeline for long audio/video transcriptions and returns a ZIP with MP4 + PDF + optional JSON/VTT.

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
      jobs/
      processing/
      workers/
      shared/
      main.py
      settings.py
    tests/
  _data/
    proof/
    transcription/
  requirements.txt
  .env
  .env.example
```

## Requirements

- Python 3.10+ (3.12 recommended)
- Playwright browsers (required for URL captures)
- FFmpeg (required for transcription)
- Redis (required for job queue)
- Optional: Podman + Buildah for containers

## Setup (Local, No Containers)

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

3) Install Playwright browsers:
```
python -m playwright install
```

4) Start Redis (example):
```
redis-server
```

5) Copy `.env.example` to `.env` and edit as needed.

## Environment Variables

All variables defined in `settings.py` must exist in `.env` and `.env.example`.

Proof Service:
- `OUTPUT_ROOT`, `LOGS_DIR`, `TSA_URL`, `FORENSIC_USN_SAMPLE_LINES`
- `CAPTURE_NAV_TIMEOUT_MS`, `CAPTURE_WAIT_AFTER_MS`, `CAPTURE_WAIT_SELECTOR`, `CAPTURE_HEADLESS`
- `OUTPUT_KEEP_DIR`

Transcription Service:
- `TRANSCRIPTION_OUTPUT_ROOT`, `TRANSCRIPTION_LOGS_DIR`, `TRANSCRIPTION_KEEP_DIR`
- `TRANSCRIPTION_DEFAULT_LANG`, `TRANSCRIPTION_ENGINE`, `TRANSCRIPTION_FW_MODEL`
- `TRANSCRIPTION_FW_DEVICE`, `TRANSCRIPTION_FW_COMPUTE`, `TRANSCRIPTION_FW_BEAM_SIZE`
- `TRANSCRIPTION_FW_VAD_FILTER`, `TRANSCRIPTION_SPONSOR_TEXT`
- `STORAGE_ROOT`, `REDIS_URL`, `RQ_RETRY_MAX`, `RQ_RETRY_INTERVAL`, `RQ_RETRY_INTERVALS`
- `MAX_PARALLEL_CHUNKS`, `CHUNK_MODE`, `SILENCE_DB`, `SILENCE_MIN_DURATION`, `MAX_CHUNK_SECONDS`
- `VAD_THRESHOLD`, `VAD_MIN_SPEECH_MS`, `VAD_MIN_SILENCE_MS`, `VAD_MAX_SPEECH_SECONDS`, `SILERO_VAD_MODEL_PATH`

## Run the Proof API (Local)

From the repo root:
```
$env:PYTHONPATH = ".\proof-service"
python -m proof_service.main
```

Or, using Uvicorn directly:
```
uvicorn proof_service.main:app --reload --app-dir .\proof-service
```

## Run the Transcription API + Workers (Local)

API:
```
$env:PYTHONPATH = ".\transcription-service"
python -m transcription_service.main
```

Workers (each in a separate terminal):
```
$env:PYTHONPATH = ".\transcription-service"
python -m transcription_service.workers.splitter
python -m transcription_service.workers.transcriber
python -m transcription_service.workers.merger
python -m transcription_service.workers.packager
```

## Job-Based Transcription API

### Create Job (URL or Path)

```
POST /v1/transcriptions/jobs
{
  "input": {"type": "url", "value": "https://x.com/i/spaces/ID"},
  "options": {"language": "es", "chunk_mode": "silence", "max_parallel_chunks": 2}
}
```

### Create Job (Upload)

```
curl -X POST http://localhost:8002/v1/transcriptions/jobs \
  -F input_type=upload \
  -F file=@"/path/to/video.mp4" \
  -F options='{"language":"es","produce_vtt":true,"produce_json":true,"produce_pdf":true}'
```

### Get Job Status

```
GET /v1/transcriptions/jobs/<job_id>
```

### Get Result Metadata

```
GET /v1/transcriptions/jobs/<job_id>/result
```

### Download ZIP

```
GET /v1/transcriptions/jobs/<job_id>/download
```

### Cancel Job (Optional)

```
POST /v1/transcriptions/jobs/<job_id>/cancel
```

## Storage Layout (Transcription)

```
_data/transcription/jobs/<job_id>/
  input/
    original.mp4
    audio.wav
  chunks/
    0001.wav
    0002.wav
  partials/
    0001.json
    0002.json
  merged/
    final.json
    final.txt
    final.vtt
  output/
    transcript.pdf
    sealium_transcription_<job_id>.zip
  logs/
    job.log
```

## Podman + Buildah (Local Dev)

1) Install Podman + Buildah.
2) Copy `.env.example` to `.env` and edit as needed.
3) Build images and start services:

```
./scripts/build-images.sh
./scripts/dev-up.sh
```

Or with a single command:
```
podman compose up --build -d
```

Services:
- Proof API: http://localhost:8001
- Transcription API: http://localhost:8002

Workers are started via `podman compose` and share the same image.
To scale transcribers:
```
podman compose up -d --scale transcription-transcriber=2
```

## Logs and Job State

- Job state is stored in `<STORAGE_ROOT>/jobs/<job_id>/job_state.json` and cached in Redis.
- Errors are appended to `logs/job.log` per job.

## Tests

```
cd proof-service
python -m pytest

cd ..\transcription-service
python -m pytest
```
