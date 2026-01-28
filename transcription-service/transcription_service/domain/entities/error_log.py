from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel
from uuid import uuid4


class ErrorLog(BaseModel):
    id: str = str(uuid4())
    timestamp_utc: datetime = datetime.utcnow()
    message: str
    stack_trace: Optional[str] = None
    context_data: Dict = {}
