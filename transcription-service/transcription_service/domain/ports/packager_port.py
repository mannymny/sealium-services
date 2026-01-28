from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PackagerPort(ABC):
    @abstractmethod
    def create_zip(self, source_dir: Path, zip_path: Path) -> Path:
        raise NotImplementedError
