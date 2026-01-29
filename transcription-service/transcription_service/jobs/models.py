from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class JobInput(BaseModel):
    type: Literal["url", "path", "upload"]
    value: str


class JobOptions(BaseModel):
    language: str
    chunk_mode: Literal["silence", "vad"] = "silence"
    max_parallel_chunks: int = 2
    produce_vtt: bool = True
    produce_json: bool = True
    produce_pdf: bool = True
    cookies_from_browser: str | None = None


class JobProgress(BaseModel):
    chunks_total: int = 0
    chunks_done: int = 0
    percent: int = 0


class JobTimestamps(BaseModel):
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None


class JobResult(BaseModel):
    zip_path: str | None = None
    download_name: str | None = None


class JobState(BaseModel):
    job_id: str
    status: Literal[
        "queued",
        "splitting",
        "transcribing",
        "merging",
        "packaging",
        "done",
        "failed",
        "canceled",
    ]
    progress: JobProgress = Field(default_factory=JobProgress)
    timestamps: JobTimestamps
    input: JobInput
    options: JobOptions
    errors: list[str] = Field(default_factory=list)
    result: JobResult | None = None

    def with_error(self, message: str) -> "JobState":
        self.errors.append(message)
        return self
