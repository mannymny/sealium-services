from __future__ import annotations

import json
import shutil
import traceback
from pathlib import Path
from datetime import datetime, timezone

from rq import Worker

from ..settings import settings
from ..jobs.paths import JobPaths
from ..jobs.store import JobStore
from ..jobs.logger import JobLogger
from ..jobs.queue import QUEUE_PACKAGER, get_redis
from ..jobs.utils import storage_root
from ..infrastructure.pdf.reportlab_adapter import ReportLabPdfWriterAdapter
from ..infrastructure.packaging.zip_packager import ZipPackagerAdapter
from ..shared.fs__shared_util import ensure_directory, hash_file_sha256


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_final_text(paths: JobPaths) -> list[str]:
    if not paths.final_txt.exists():
        return []
    lines = paths.final_txt.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _write_manifest(paths: JobPaths, job_id: str) -> Path:
    payload = {
        "job_id": job_id,
        "created_at": _now_iso(),
        "files": {},
    }
    for rel in [
        "input/original.mp4",
        "output/transcript.pdf",
        "merged/final.json",
        "merged/final.vtt",
        "merged/final.txt",
    ]:
        fp = paths.job_dir / rel
        if fp.exists():
            payload["files"][rel] = {
                "sha256": hash_file_sha256(fp),
                "size": fp.stat().st_size,
            }
    paths.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return paths.manifest_path


def _zip_add(zf, src: Path, arcname: str) -> None:
    zf.write(src, arcname)


def _build_zip(paths: JobPaths, job_id: str, produce_json: bool, produce_vtt: bool) -> Path:
    ensure_directory(paths.output_dir)
    zip_path = paths.output_zip()

    import zipfile

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if paths.original_mp4.exists():
            _zip_add(zf, paths.original_mp4, "video.mp4")
        if paths.output_pdf().exists():
            _zip_add(zf, paths.output_pdf(), "transcript.pdf")
        if produce_json and paths.final_json.exists():
            _zip_add(zf, paths.final_json, "transcript.json")
        if produce_vtt and paths.final_vtt.exists():
            _zip_add(zf, paths.final_vtt, "transcript.vtt")
        if paths.final_txt.exists():
            _zip_add(zf, paths.final_txt, "transcript.txt")
        if paths.manifest_path.exists():
            _zip_add(zf, paths.manifest_path, "manifest.json")
        if paths.logs_dir.exists():
            for log_file in paths.logs_dir.glob("*.log"):
                _zip_add(zf, log_file, f"logs/{log_file.name}")

    return zip_path


def package_job(job_id: str) -> None:
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        return
    if job.status == "canceled":
        return

    paths = JobPaths(storage_root(), job_id)
    logger = JobLogger(paths.logs_dir / "job.log")

    try:
        store.set_status(job_id, "packaging")
        ensure_directory(paths.output_dir)

        pdf_writer = ReportLabPdfWriterAdapter()

        produce_pdf = bool(job.options.produce_pdf)
        if produce_pdf:
            transcript_lines = _load_final_text(paths)
            pdf_writer.write_pdf(
                paths.output_pdf(),
                title=f"Transcription {job_id}",
                source_url=job.input.value if job.input.type == "url" else None,
                transcript_lines=transcript_lines,
                sponsor_text=settings.TRANSCRIPTION_SPONSOR_TEXT,
            )

        _write_manifest(paths, job_id)

        zip_path = _build_zip(paths, job_id, bool(job.options.produce_json), bool(job.options.produce_vtt))

        store.update(
            job_id,
            result={
                "zip_path": str(zip_path),
                "download_name": zip_path.name,
            },
        )
        store.set_status(job_id, "done")
        logger.write("packager completed")
    except Exception as exc:
        store.add_error(job_id, str(exc))
        store.set_status(job_id, "failed")
        logger.write(traceback.format_exc())
        raise


def main() -> None:
    worker = Worker([QUEUE_PACKAGER], connection=get_redis())
    worker.work()


if __name__ == "__main__":
    main()
