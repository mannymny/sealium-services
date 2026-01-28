from abc import ABC, abstractmethod

class TimeStampingPort(ABC):
    @abstractmethod
    async def timestamp_file(self, file_path: str, output_dir: str) -> str:
        pass