from __future__ import annotations

from pathlib import Path

from ..settings import settings


def _find_repo_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / ".env").exists():
            return parent
    parents = list(start.parents)
    return parents[3] if len(parents) > 3 else start.parent


def resolve_path(path_value: str) -> Path:
    base_dir = _find_repo_root(Path(__file__).resolve())
    p = Path(path_value)
    if p.is_absolute():
        return p
    return base_dir / p


def storage_root() -> Path:
    return resolve_path(settings.STORAGE_ROOT)
