from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from redis import Redis

from .models import JobState


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, storage_root: Path, *, redis_url: str | None = None, redis_client: Redis | None = None):
        self.storage_root = Path(storage_root)
        if redis_client is not None:
            self.redis = redis_client
        elif redis_url:
            self.redis = Redis.from_url(redis_url)
        else:
            self.redis = None

    def _key(self, job_id: str) -> str:
        return f"transcription:job:{job_id}"

    def _state_path(self, job_id: str) -> Path:
        return self.storage_root / "jobs" / job_id / "job_state.json"

    def _write_file(self, job_id: str, payload: dict) -> None:
        path = self._state_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _read_file(self, job_id: str) -> dict | None:
        path = self._state_path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def create(self, state: JobState) -> None:
        payload = state.model_dump()
        self._write_file(state.job_id, payload)
        if self.redis is not None:
            self.redis.set(self._key(state.job_id), json.dumps(payload))

    def load(self, job_id: str) -> JobState | None:
        payload = None
        if self.redis is not None:
            raw = self.redis.get(self._key(job_id))
            if raw:
                payload = json.loads(raw)
        if payload is None:
            payload = self._read_file(job_id)
        if payload is None:
            return None
        return JobState.model_validate(payload)

    def save(self, state: JobState) -> None:
        payload = state.model_dump()
        self._write_file(state.job_id, payload)
        if self.redis is not None:
            self.redis.set(self._key(state.job_id), json.dumps(payload))

    def update(self, job_id: str, **updates) -> JobState | None:
        state = self.load(job_id)
        if not state:
            return None

        data = state.model_dump()
        for key, value in updates.items():
            if key in data:
                data[key] = value

        data["timestamps"]["updated_at"] = now_iso()
        state = JobState.model_validate(data)
        self.save(state)
        return state

    def set_status(self, job_id: str, status: str) -> JobState | None:
        state = self.load(job_id)
        if not state:
            return None
        data = state.model_dump()
        data["status"] = status
        data["timestamps"]["updated_at"] = now_iso()
        if status in {"splitting", "transcribing", "merging", "packaging"} and not data["timestamps"].get("started_at"):
            data["timestamps"]["started_at"] = now_iso()
        if status in {"done", "failed", "canceled"}:
            data["timestamps"]["finished_at"] = now_iso()
        state = JobState.model_validate(data)
        self.save(state)
        return state

    def set_progress(self, job_id: str, *, chunks_total: int | None = None, chunks_done: int | None = None) -> JobState | None:
        state = self.load(job_id)
        if not state:
            return None
        data = state.model_dump()
        progress = data.get("progress", {})
        if chunks_total is not None:
            progress["chunks_total"] = int(chunks_total)
        if chunks_done is not None:
            progress["chunks_done"] = int(chunks_done)
        total = progress.get("chunks_total", 0) or 0
        done = progress.get("chunks_done", 0) or 0
        progress["percent"] = int((done / total) * 100) if total > 0 else 0
        data["progress"] = progress
        data["timestamps"]["updated_at"] = now_iso()
        state = JobState.model_validate(data)
        self.save(state)
        return state

    def add_error(self, job_id: str, message: str) -> JobState | None:
        state = self.load(job_id)
        if not state:
            return None
        data = state.model_dump()
        data.setdefault("errors", []).append(message)
        data["timestamps"]["updated_at"] = now_iso()
        state = JobState.model_validate(data)
        self.save(state)
        return state
