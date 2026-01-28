from __future__ import annotations

import shutil
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

from ...domain.entities.error_log import ErrorLog
from ...domain.entities.transcription_case import TranscriptionCase
from ...domain.ports.error_monitor_port import ErrorMonitorPort
from ...domain.ports.packager_port import PackagerPort
from ...domain.ports.pdf_writer_port import PdfWriterPort
from ...domain.ports.transcriber_port import TranscriberPort
from ...domain.ports.media_converter_port import MediaConverterPort
from ...shared.fs__shared_util import ensure_directory, hash_file_sha256, safe_path_component


class CreateFileTranscriptionUseCase:
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

    async def execute(self, path: str, *, lang: str) -> dict:
        temp_dir = None
        try:
            self.output_root.mkdir(parents=True, exist_ok=True)
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")

            src_path = Path(path).expanduser()
            if not src_path.exists():
                raise RuntimeError(f"Local file not found: {src_path}")

            if self.keep_dir:
                case_dir = ensure_directory(self.output_root / f"{ts_str}_local_{safe_path_component(src_path.stem, max_len=80)}")
            else:
                temp_dir = tempfile.TemporaryDirectory(dir=self.output_root)
                case_dir = Path(temp_dir.name)

            media_path = case_dir / src_path.name
            if src_path.resolve() != media_path.resolve():
                shutil.copy2(src_path, media_path)

            media_path = self.converter.ensure_mp4(media_path, case_dir)

            case = TranscriptionCase(case_type="FILE", input_target=str(src_path), output_dir=str(case_dir))

            result = self.transcriber.transcribe(media_path, case_dir, lang=lang)

            pdf_path = case_dir / f"{media_path.stem}_transcription.pdf"
            self.pdf_writer.write_pdf(
                pdf_path,
                title=case_dir.name,
                source_url=str(src_path),
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

            if not self.keep_dir and temp_dir is not None:
                temp_dir.cleanup()

            result_payload = {
                "status": "success",
                "case_id": case.id,
                "zip_path": str(zip_path),
            }
            if self.keep_dir:
                result_payload["path"] = str(case_dir)

            return result_payload

        except Exception as e:
            await self.monitor.log_error(
                ErrorLog(
                    message=str(e),
                    stack_trace=traceback.format_exc(),
                    context_data={"path": path},
                )
            )
            raise e
