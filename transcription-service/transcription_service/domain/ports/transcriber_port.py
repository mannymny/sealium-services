from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptionResult:
    txt_path: Path
    lines: list[str]
    full_text: str
    duration_sec: int


class TranscriberPort(ABC):
    @abstractmethod
    def transcribe(self, media_path: Path, out_dir: Path, *, lang: str) -> TranscriptionResult:
        raise NotImplementedError
