import pytest
from pathlib import Path

from transcription_service.application.use_cases.batch_transcribe import BatchTranscriptionUseCase
from transcription_service.application.use_cases.download_all_audio import DownloadAllAudioUseCase
from transcription_service.application.use_cases.create_url_transcription import CreateUrlTranscriptionUseCase
from transcription_service.application.use_cases.create_file_transcription import CreateFileTranscriptionUseCase
from transcription_service.domain.ports.transcriber_port import TranscriptionResult


class DummyDownloader:
    def download(self, url: str, out_dir: Path, *, cookies_from_browser: str | None = None) -> Path:
        item_dir = out_dir / "Name - Test Space ID - 123"
        item_dir.mkdir(parents=True, exist_ok=True)
        media_path = item_dir / "media.mp4"
        media_path.write_text("dummy", encoding="utf-8")
        return media_path

    def download_all_audio(self, url: str, input_dir: Path, *, audio_format: str, cookies_from_browser: str | None = None) -> None:
        input_dir.mkdir(parents=True, exist_ok=True)


class DummyTranscriber:
    def transcribe(self, media_path: Path, out_dir: Path, *, lang: str) -> TranscriptionResult:
        txt_path = out_dir / f"{media_path.stem}.txt"
        txt_path.write_text("Duration: 0:10\n\n[00:00:00] -> [00:01:00] hola", encoding="utf-8")
        return TranscriptionResult(
            txt_path=txt_path,
            lines=["Duration: 0:10", "", "[00:00:00] -> [00:01:00] hola"],
            full_text="hola",
            duration_sec=10,
        )


class DummyPdfWriter:
    def write_pdf(self, pdf_path: Path, *, title: str | None, source_url: str | None, transcript_lines, sponsor_text: str):
        pdf_path.write_text("pdf", encoding="utf-8")
        return pdf_path


class DummyPackager:
    def create_zip(self, source_dir: Path, zip_path: Path) -> Path:
        zip_path.write_text("zip", encoding="utf-8")
        return zip_path


class DummyConverter:
    def ensure_mp4(self, input_path: Path, out_dir: Path) -> Path:
        return input_path


class DummyMonitor:
    async def log_error(self, error):
        return None


@pytest.mark.asyncio
async def test_create_url_transcription_success(tmp_path: Path):
    use_case = CreateUrlTranscriptionUseCase(
        DummyDownloader(),
        DummyTranscriber(),
        DummyPdfWriter(),
        DummyPackager(),
        DummyMonitor(),
        str(tmp_path),
        keep_dir=True,
    )

    result = await use_case.execute("https://x.com/i/spaces/123", lang="es")
    assert result["status"] == "success"
    assert "zip_path" in result
    assert "path" in result


@pytest.mark.asyncio
async def test_create_file_transcription_success(tmp_path: Path):
    src = tmp_path / "input.mp4"
    src.write_text("dummy", encoding="utf-8")

    use_case = CreateFileTranscriptionUseCase(
        DummyTranscriber(),
        DummyPdfWriter(),
        DummyPackager(),
        DummyConverter(),
        DummyMonitor(),
        str(tmp_path),
        keep_dir=True,
    )

    result = await use_case.execute(str(src), lang="es")
    assert result["status"] == "success"
    assert "zip_path" in result
    assert "path" in result


@pytest.mark.asyncio
async def test_download_all_audio_success(tmp_path: Path):
    use_case = DownloadAllAudioUseCase(DummyDownloader(), DummyMonitor())
    result = await use_case.execute(
        "https://www.youtube.com/@example",
        input_dir=str(tmp_path / "input"),
        audio_format="m4a",
    )
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_batch_transcription_success(tmp_path: Path):
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    audio_path = input_dir / "sample.mp4"
    audio_path.write_text("dummy", encoding="utf-8")

    use_case = BatchTranscriptionUseCase(
        DummyTranscriber(),
        DummyPdfWriter(),
        DummyPackager(),
        DummyConverter(),
        DummyMonitor(),
        str(tmp_path / "output"),
        keep_dir=True,
    )

    result = await use_case.execute(str(input_dir), lang="es")
    assert result["status"] == "success"
    assert result["count"] == 1
