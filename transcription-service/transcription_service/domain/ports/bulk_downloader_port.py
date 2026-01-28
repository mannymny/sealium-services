from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BulkDownloaderPort(ABC):
    @abstractmethod
    def download_all_audio(
        self,
        url: str,
        input_dir: Path,
        *,
        audio_format: str,
        cookies_from_browser: str | None = None,
    ) -> None:
        raise NotImplementedError
