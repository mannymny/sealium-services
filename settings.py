from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    TSA_URL: str = "http://timestamp.sectigo.com/rfc3161"
    OUTPUT_ROOT: str = "./proof_output"
    LOGS_DIR: str = "./logs"
    FORENSIC_USN_SAMPLE_LINES: int = 6000

settings = Settings()