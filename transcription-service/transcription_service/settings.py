from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_PATH, env_file_encoding="utf-8")

    TRANSCRIPTION_OUTPUT_ROOT: str = "./transcription_output"
    TRANSCRIPTION_LOGS_DIR: str = "./logs"
    TRANSCRIPTION_KEEP_DIR: bool = True

    TRANSCRIPTION_DEFAULT_LANG: str = "es"
    TRANSCRIPTION_ENGINE: str = "faster-whisper"
    TRANSCRIPTION_FW_MODEL: str = "base"
    TRANSCRIPTION_FW_DEVICE: str = "cpu"
    TRANSCRIPTION_FW_COMPUTE: str = "int8"
    TRANSCRIPTION_FW_BEAM_SIZE: int = 2
    TRANSCRIPTION_FW_VAD_FILTER: bool = False
    TRANSCRIPTION_SPONSOR_TEXT: str = "Esta transcripcion fue patrocinada por mi Deus Raed, Akuuuuum"

    STORAGE_ROOT: str = "./_data/transcription"

    REDIS_URL: str = "redis://localhost:6379/0"
    RQ_RETRY_MAX: int = 3
    RQ_RETRY_INTERVAL: int = 60
    RQ_RETRY_INTERVALS: str | None = "10,60,300"

    MAX_PARALLEL_CHUNKS: int = 2
    CHUNK_MODE: str = "silence"

    SILENCE_DB: str = "-35dB"
    SILENCE_MIN_DURATION: float = 0.6
    MAX_CHUNK_SECONDS: int = 120

    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SPEECH_MS: int = 250
    VAD_MIN_SILENCE_MS: int = 200
    VAD_MAX_SPEECH_SECONDS: int = 120
    SILERO_VAD_MODEL_PATH: str | None = None


settings = Settings()
