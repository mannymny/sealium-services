from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable


class PdfWriterPort(ABC):
    @abstractmethod
    def write_pdf(
        self,
        pdf_path: Path,
        *,
        title: str | None,
        source_url: str | None,
        transcript_lines: Iterable[str],
        sponsor_text: str,
    ) -> Path:
        raise NotImplementedError
