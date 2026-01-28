from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, env_file_encoding="utf-8")

    TRANSCRIPTION_OUTPUT_ROOT: str
    TRANSCRIPTION_LOGS_DIR: str
    TRANSCRIPTION_KEEP_DIR: bool

    TRANSCRIPTION_DEFAULT_LANG: str = "es"
    TRANSCRIPTION_ENGINE: str = "faster-whisper"
    TRANSCRIPTION_FW_MODEL: str = "base"
    TRANSCRIPTION_FW_DEVICE: str = "cpu"
    TRANSCRIPTION_FW_COMPUTE: str = "int8"
    TRANSCRIPTION_SPONSOR_TEXT: str = "Esta transcripcion fue patrocinada por mi Deus Raed, Akuuuuum"


settings = Settings()
