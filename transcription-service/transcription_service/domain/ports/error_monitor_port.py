from __future__ import annotations

from abc import ABC, abstractmethod
from ..entities.error_log import ErrorLog


class ErrorMonitorPort(ABC):
    @abstractmethod
    async def log_error(self, error: ErrorLog) -> None:
        raise NotImplementedError
