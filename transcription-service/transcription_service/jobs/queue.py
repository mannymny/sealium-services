from __future__ import annotations

from typing import Iterable

from redis import Redis
from rq import Queue
from rq.retry import Retry

from ..settings import settings


QUEUE_SPLITTER = "transcription-splitter"
QUEUE_TRANSCRIBER = "transcription-transcriber"
QUEUE_MERGER = "transcription-merger"
QUEUE_PACKAGER = "transcription-packager"


def get_redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL)


def get_queue(name: str) -> Queue:
    return Queue(name, connection=get_redis())


def parse_retry_intervals(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None
    intervals: list[int] = []
    for p in parts:
        try:
            intervals.append(int(p))
        except ValueError:
            continue
    return intervals or None


def build_retry() -> Retry | None:
    if settings.RQ_RETRY_MAX <= 0:
        return None
    intervals = parse_retry_intervals(settings.RQ_RETRY_INTERVALS)
    if intervals:
        return Retry(max=settings.RQ_RETRY_MAX, interval=intervals)
    return Retry(max=settings.RQ_RETRY_MAX, interval=settings.RQ_RETRY_INTERVAL)


def enqueue(queue_name: str, func, *args, **kwargs):
    retry = build_retry()
    q = get_queue(queue_name)
    return q.enqueue(func, *args, retry=retry, **kwargs)


def queue_names() -> Iterable[str]:
    return [QUEUE_SPLITTER, QUEUE_TRANSCRIBER, QUEUE_MERGER, QUEUE_PACKAGER]
