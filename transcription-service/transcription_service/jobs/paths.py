from __future__ import annotations

from pathlib import Path


class JobPaths:
    def __init__(self, storage_root: Path, job_id: str):
        self.storage_root = storage_root
        self.job_id = job_id
        self.job_dir = storage_root / "jobs" / job_id

        self.input_dir = self.job_dir / "input"
        self.chunks_dir = self.job_dir / "chunks"
        self.partials_dir = self.job_dir / "partials"
        self.merged_dir = self.job_dir / "merged"
        self.output_dir = self.job_dir / "output"
        self.logs_dir = self.job_dir / "logs"

        self.state_path = self.job_dir / "job_state.json"
        self.chunks_meta_path = self.job_dir / "chunks.json"
        self.manifest_path = self.job_dir / "manifest.json"

    @property
    def original_mp4(self) -> Path:
        return self.input_dir / "original.mp4"

    @property
    def audio_wav(self) -> Path:
        return self.input_dir / "audio.wav"

    @property
    def final_json(self) -> Path:
        return self.merged_dir / "final.json"

    @property
    def final_txt(self) -> Path:
        return self.merged_dir / "final.txt"

    @property
    def final_vtt(self) -> Path:
        return self.merged_dir / "final.vtt"

    def chunk_path(self, index: int) -> Path:
        return self.chunks_dir / f"{index:04d}.wav"

    def partial_path(self, index: int) -> Path:
        return self.partials_dir / f"{index:04d}.json"

    def output_zip(self) -> Path:
        return self.output_dir / f"sealium_transcription_{self.job_id}.zip"

    def output_pdf(self) -> Path:
        return self.output_dir / "transcript.pdf"
