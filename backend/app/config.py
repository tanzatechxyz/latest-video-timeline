from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")
    host: str = "0.0.0.0"
    port: int = 8080
    base_url: str = "http://localhost:8080"
    db_path: str = "/data/review_queue.db"
    root_folder: str = "/videos"
    data_dir: str = "/data"
    supported_extensions: str = ".mp4,.mov,.m4v,.webm,.mkv"
    watched_threshold_percent: int = 95
    sort_priority: str = "filename,metadata,filesystem"
    auto_advance_on_done: bool = True
    auto_advance_on_end: bool = True
    generate_thumbnails: bool = False
    thumbnail_interval_seconds: int = 3
    thumbnail_width: int = 480
    auth_enabled: bool = False
    username: str = "admin"
    password: str = "changeme"
    secret_key: str = "change-this-in-production"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    auto_scan_on_startup: bool = True
    scan_interval_seconds: int = 10800
    scan_on_settings_save: bool = False

    @property
    def sqlalchemy_database_uri(self) -> str:
        return f"sqlite:///{self.db_path}"
    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)
    @property
    def thumbnails_path(self) -> Path:
        return self.data_path / "thumbnails"
    @property
    def frontend_build_path(self) -> Path:
        return Path(__file__).resolve().parent / "static" / "client"
    @property
    def cors_origins_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
    @field_validator("watched_threshold_percent")
    @classmethod
    def validate_threshold(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("watched threshold percent must be between 1 and 100")
        return value


settings = Settings()
