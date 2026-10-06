from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND_DIR / "data"
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "camera_monitor.db"
DEFAULT_LOG_DIR = DEFAULT_DATA_DIR / "logs"


MIN_INTERVAL_SECONDS: int = 10
MAX_INTERVAL_SECONDS: int = 31_536_000


class Settings(BaseSettings):
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    database_url: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    monitor_interval_seconds: int = 60
    frontend_dist: Path | None = None
    log_dir: Path = DEFAULT_LOG_DIR

    @field_validator("monitor_interval_seconds")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < MIN_INTERVAL_SECONDS or v > MAX_INTERVAL_SECONDS:
            msg = (
                f"monitor_interval_seconds must be between {MIN_INTERVAL_SECONDS} "
                f"and {MAX_INTERVAL_SECONDS} seconds"
            )
            raise ValueError(msg)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
