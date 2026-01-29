from datetime import datetime, timezone

from transcription_service.jobs.models import JobInput, JobOptions, JobState, JobTimestamps
from transcription_service.jobs.store import JobStore


def test_job_store_transitions(tmp_path):
    store = JobStore(tmp_path)
    ts = datetime.now(timezone.utc).isoformat()

    state = JobState(
        job_id="job-1",
        status="queued",
        timestamps=JobTimestamps(created_at=ts, updated_at=ts),
        input=JobInput(type="url", value="http://example.com"),
        options=JobOptions(language="es"),
    )

    store.create(state)
    loaded = store.load("job-1")
    assert loaded is not None
    assert loaded.status == "queued"

    store.set_status("job-1", "splitting")
    store.set_progress("job-1", chunks_total=10, chunks_done=3)
    updated = store.load("job-1")

    assert updated.status == "splitting"
    assert updated.progress.chunks_total == 10
    assert updated.progress.chunks_done == 3
    assert updated.progress.percent == 30
    assert updated.timestamps.started_at is not None

    store.set_status("job-1", "done")
    finished = store.load("job-1")
    assert finished is not None
    assert finished.status == "done"
    assert finished.timestamps.finished_at is not None
