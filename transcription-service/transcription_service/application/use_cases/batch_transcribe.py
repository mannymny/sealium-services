from __future__ import annotations

import shutil
import traceback
from pathlib import Path

from ...domain.entities.error_log import ErrorLog
from ...domain.entities.transcription_case import TranscriptionCase
from ...domain.ports.error_monitor_port import ErrorMonitorPort
from ...domain.ports.packager_port import PackagerPort
from ...domain.ports.pdf_writer_port import PdfWriterPort
from ...domain.ports.transcriber_port import TranscriberPort
from ...domain.ports.media_converter_port import MediaConverterPort
from ...shared.fs__shared_util import ensure_directory, hash_file_sha256, safe_path_component


class BatchTranscriptionUseCase:
    def __init__(
        self,
        transcriber: TranscriberPort,
        pdf_writer: PdfWriterPort,
        packager: PackagerPort,
        converter: MediaConverterPort,
        monitor: ErrorMonitorPort,
        output_root: str,
        *,
        keep_dir: bool = True,
        sponsor_text: str = "",
    ):
        self.transcriber = transcriber
        self.pdf_writer = pdf_writer
        self.packager = packager
        self.converter = converter
        self.monitor = monitor
        self.output_root = Path(output_root)
        self.keep_dir = keep_dir
        self.sponsor_text = sponsor_text or "Esta transcripcion fue patrocinada por mi Deus Raed, Akuuuuum"

    def _is_already_done(self, item_dir: Path) -> bool:
        if not item_dir.exists():
            return False
        has_txt = any(item_dir.glob("*.txt"))
        has_pdf = any(item_dir.glob("*_transcription.pdf"))
        return has_txt or has_pdf

    def _iter_input_audio_files(self, input_dir: Path) -> list[Path]:
        exts = {".m4a", ".mp3", ".wav", ".aac", ".webm", ".flac", ".ogg", ".mp4", ".mkv"}
        files: list[Path] = []
        if not input_dir.exists():
            return files

        for p in input_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                files.append(p)

        files.sort(key=lambda x: x.stat().st_mtime)
        return files

    async def execute(self, input_dir: str, *, lang: str) -> dict:
        try:
            in_dir = Path(input_dir)
            audio_files = self._iter_input_audio_files(in_dir)
            if not audio_files:
                return {"status": "empty", "count": 0, "results": []}

            results: list[dict] = []
            for audio_path in audio_files:
                safe_name = safe_path_component(audio_path.stem, max_len=80)
                case_dir = self.output_root / f"Input - {safe_name}"

                if self._is_already_done(case_dir):
                    continue

                ensure_directory(case_dir)

                local_media = case_dir / audio_path.name
                if audio_path.resolve() != local_media.resolve():
                    shutil.copy2(audio_path, local_media)

                local_media = self.converter.ensure_mp4(local_media, case_dir)

                case = TranscriptionCase(case_type="BATCH", input_target=str(audio_path), output_dir=str(case_dir))

                result = self.transcriber.transcribe(local_media, case_dir, lang=lang)

                pdf_path = case_dir / f"{local_media.stem}_transcription.pdf"
                self.pdf_writer.write_pdf(
                    pdf_path,
                    title=case_dir.name,
                    source_url=str(audio_path),
                    transcript_lines=result.lines,
                    sponsor_text=self.sponsor_text,
                )

                hashes_path = case_dir / "hashes.sha256"
                with open(hashes_path, "w", encoding="utf-8") as hf:
                    for path in case_dir.glob("*"):
                        if path.is_file() and path.name != "hashes.sha256":
                            h = hash_file_sha256(path)
                            case.add_artifact(path.name, hash_sha256=h)
                            hf.write(f"{h} *{path.name}\n")

                manifest_path = case_dir / "manifest.json"
                manifest_path.write_text(case.model_dump_json(indent=2), encoding="utf-8")

                zip_name = f"{safe_path_component(case_dir.name, max_len=80)}.zip"
                zip_path = self.output_root / zip_name
                self.packager.create_zip(case_dir, zip_path)

                results.append({
                    "status": "success",
                    "case_id": case.id,
                    "zip_path": str(zip_path),
                    "path": str(case_dir),
                })

                if not self.keep_dir:
                    shutil.rmtree(case_dir, ignore_errors=True)

            return {"status": "success", "count": len(results), "results": results}

        except Exception as e:
            await self.monitor.log_error(
                ErrorLog(
                    message=str(e),
                    stack_trace=traceback.format_exc(),
                    context_data={"input_dir": input_dir},
                )
            )
            raise e
