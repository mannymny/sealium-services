from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, env_file_encoding="utf-8")

    TSA_URL: str
    OUTPUT_ROOT: str
    LOGS_DIR: str
    FORENSIC_USN_SAMPLE_LINES: int
    CAPTURE_NAV_TIMEOUT_MS: int
    CAPTURE_WAIT_AFTER_MS: int
    CAPTURE_WAIT_SELECTOR: str
    CAPTURE_HEADLESS: bool
    OUTPUT_KEEP_DIR: bool

settings = Settings()
