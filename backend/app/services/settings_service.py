from __future__ import annotations

from sqlalchemy.orm import Session
from app.config import settings as env_settings
from app.models import AppSettings

DEFAULT_SETTINGS_ID = 1


def get_or_create_settings(db: Session) -> AppSettings:
    settings = db.get(AppSettings, DEFAULT_SETTINGS_ID)
    if settings:
        if settings.sort_priority_csv == "filename,metadata,filesystem":
            settings.sort_priority_csv = env_settings.sort_priority
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings
    settings = AppSettings(id=DEFAULT_SETTINGS_ID, root_folder=env_settings.root_folder, supported_extensions_csv=env_settings.supported_extensions, watched_threshold_percent=env_settings.watched_threshold_percent, sort_priority_csv=env_settings.sort_priority, auto_advance_on_done=env_settings.auto_advance_on_done, auto_advance_on_end=env_settings.auto_advance_on_end, generate_thumbnails=env_settings.generate_thumbnails, thumbnail_interval_seconds=env_settings.thumbnail_interval_seconds, thumbnail_width=env_settings.thumbnail_width)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings
