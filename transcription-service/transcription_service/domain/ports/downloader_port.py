from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class DownloaderPort(ABC):
    @abstractmethod
    def download(self, url: str, out_dir: Path, *, cookies_from_browser: str | None = None) -> Path:
        raise NotImplementedError
