from abc import ABC, abstractmethod

class UrlCapturePort(ABC):
    @abstractmethod
    async def capture(self, url: str, destination_dir: str) -> None:
        pass

class FileForensicPort(ABC):
    @abstractmethod
    async def collect_metadata(self, file_path: str, destination_dir: str) -> None:
        pass
    @abstractmethod
    async def collect_system_logs(self, destination_dir: str) -> None:
        pass