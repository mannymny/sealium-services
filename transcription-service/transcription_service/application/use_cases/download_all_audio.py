from __future__ import annotations

import traceback
from pathlib import Path

from ...domain.entities.error_log import ErrorLog
from ...domain.ports.bulk_downloader_port import BulkDownloaderPort
from ...domain.ports.error_monitor_port import ErrorMonitorPort
from ...shared.fs__shared_util import ensure_directory


class DownloadAllAudioUseCase:
    def __init__(self, downloader: BulkDownloaderPort, monitor: ErrorMonitorPort):
        self.downloader = downloader
        self.monitor = monitor

    async def execute(
        self,
        url: str,
        *,
        input_dir: str,
        audio_format: str,
        cookies_from_browser: str | None = None,
    ) -> dict:
        try:
            target_dir = ensure_directory(Path(input_dir))
            self.downloader.download_all_audio(
                url,
                target_dir,
                audio_format=audio_format,
                cookies_from_browser=cookies_from_browser,
            )
            return {"status": "success", "input_dir": str(target_dir)}
        except Exception as e:
            await self.monitor.log_error(
                ErrorLog(
                    message=str(e),
                    stack_trace=traceback.format_exc(),
                    context_data={"url": url, "input_dir": input_dir},
                )
            )
            raise e
