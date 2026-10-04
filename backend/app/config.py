from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND_DIR / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "camera_monitor.db"


class Settings(BaseSettings):
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    monitor_interval_seconds: int = 60

    @field_validator("monitor_interval_seconds")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 10:
            msg = "monitor_interval_seconds must be at least 10 seconds"
            raise ValueError(msg)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )



settings = Settings()
