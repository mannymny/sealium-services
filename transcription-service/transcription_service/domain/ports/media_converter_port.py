from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class MediaConverterPort(ABC):
    @abstractmethod
    def ensure_mp4(self, input_path: Path, out_dir: Path) -> Path:
        raise NotImplementedError
