from __future__ import annotations

import threading
from pathlib import Path

from ..shared.fs__shared_util import remove_diacritics_to_ascii


class FasterWhisperChunkTranscriber:
    def __init__(
        self,
        *,
        model_size: str,
        device: str,
        compute_type: str,
        beam_size: int,
        vad_filter: bool,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size = beam_size
        self.vad_filter = vad_filter
        self._local = threading.local()

    def _get_model(self):
        model = getattr(self._local, "model", None)
        if model is None:
            from faster_whisper import WhisperModel

            model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            self._local.model = model
        return model

    def transcribe_chunk(self, chunk_path: Path, *, chunk_start: float, language: str) -> dict:
        model = self._get_model()

        segments, _info = model.transcribe(
            str(chunk_path),
            language=language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
        )

        out_segments: list[dict] = []
        texts: list[str] = []

        for seg in segments:
            text = remove_diacritics_to_ascii(getattr(seg, "text", "") or "")
            if not text:
                continue
            start = float(getattr(seg, "start", 0.0) or 0.0) + chunk_start
            end = float(getattr(seg, "end", 0.0) or 0.0) + chunk_start
            if end <= start:
                continue
            out_segments.append({"start": start, "end": end, "text": text})
            texts.append(text)

        return {
            "segments": out_segments,
            "text": " ".join(texts).strip(),
        }
