from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel
from uuid import uuid4


class Artifact(BaseModel):
    rel_path: str
    hash_sha256: Optional[str] = None
    metadata: Dict[str, str] = {}


class TranscriptionCase(BaseModel):
    id: str = str(uuid4())
    case_type: str
    input_target: str
    output_dir: str
    created_at_utc: datetime = datetime.utcnow()
    artifacts: List[Artifact] = []

    def add_artifact(self, rel_path: str, metadata: Dict | None = None, hash_sha256: str | None = None) -> None:
        self.artifacts.append(
            Artifact(rel_path=rel_path, metadata=metadata or {}, hash_sha256=hash_sha256)
        )
