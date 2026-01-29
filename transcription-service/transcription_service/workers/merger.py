from __future__ import annotations

import json
import traceback
from pathlib import Path

from rq import Worker

from ..settings import settings
from ..jobs.paths import JobPaths
from ..jobs.store import JobStore
from ..jobs.logger import JobLogger
from ..jobs.queue import QUEUE_MERGER, QUEUE_PACKAGER, enqueue, get_redis
from ..jobs.utils import storage_root
from ..processing.merge import merge_partials
from .packager import package_job


def merge_job(job_id: str) -> None:
    store = JobStore(storage_root(), redis_url=settings.REDIS_URL)
    job = store.load(job_id)
    if not job:
        return
    if job.status == "canceled":
        return

    paths = JobPaths(storage_root(), job_id)
    logger = JobLogger(paths.logs_dir / "job.log")

    try:
        store.set_status(job_id, "merging")
        paths.merged_dir.mkdir(parents=True, exist_ok=True)

        produce_json = bool(job.options.produce_json)
        produce_vtt = bool(job.options.produce_vtt)

        merge_partials(
            partials_dir=paths.partials_dir,
            final_json=paths.final_json,
            final_txt=paths.final_txt,
            final_vtt=paths.final_vtt if produce_vtt else None,
            produce_json=produce_json,
            produce_vtt=produce_vtt,
        )

        enqueue(QUEUE_PACKAGER, package_job, job_id)
        logger.write("merger completed")
    except Exception as exc:
        store.add_error(job_id, str(exc))
        store.set_status(job_id, "failed")
        logger.write(traceback.format_exc())
        raise


def main() -> None:
    worker = Worker([QUEUE_MERGER], connection=get_redis())
    worker.work()


if __name__ == "__main__":
    main()
