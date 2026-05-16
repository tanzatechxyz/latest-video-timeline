from __future__ import annotations

from datetime import date, datetime, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.models import Video
from app.services.settings_service import get_or_create_settings


def get_continue_video(db: Session) -> Video | None:
    return db.execute(select(Video).where(Video.is_missing.is_(False)).order_by(Video.derived_sort_date.desc().nullslast(), Video.modified_time.desc().nullslast(), Video.discovered_at.desc(), Video.filename.asc()).limit(1)).scalars().first()


def set_current_video(db: Session, video_id: str | None):
    settings = get_or_create_settings(db)
    settings.current_video_id = video_id
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def _id_list_for_view(db: Session, view: str) -> list[str]:
    stmt = select(Video.id).where(Video.is_missing.is_(False))
    if view == "unfinished":
        stmt = stmt.where(Video.review_state == "queued")
    elif view == "watched":
        stmt = stmt.where(Video.review_state == "watched")
    elif view == "skipped":
        stmt = stmt.where(Video.review_state == "skipped")
    elif view == "bookmarked":
        stmt = stmt.where(Video.bookmarked.is_(True))
    stmt = stmt.order_by(Video.derived_sort_date.desc().nullslast(), Video.modified_time.desc().nullslast(), Video.discovered_at.desc(), Video.filename.asc())
    return list(db.execute(stmt).scalars().all())


def get_queue_position(db: Session, video_id: str, view: str = "unfinished") -> tuple[int | None, int]:
    ids = _id_list_for_view(db, view)
    total = len(ids)
    try:
        return ids.index(video_id) + 1, total
    except ValueError:
        return None, total


def get_adjacent_video_ids(db: Session, video: Video, view: str = "unfinished") -> tuple[str | None, str | None]:
    ids = _id_list_for_view(db, view)
    if video.id not in ids:
        return None, None
    idx = ids.index(video.id)
    return (ids[idx - 1] if idx > 0 else None, ids[idx + 1] if idx < len(ids) - 1 else None)


def jump_to_date(db: Session, target_date: date, view: str = "unfinished") -> Video | None:
    stmt = select(Video).where(Video.is_missing.is_(False))
    if view == "unfinished":
        stmt = stmt.where(Video.review_state == "queued")
    elif view == "watched":
        stmt = stmt.where(Video.review_state == "watched")
    elif view == "skipped":
        stmt = stmt.where(Video.review_state == "skipped")
    elif view == "bookmarked":
        stmt = stmt.where(Video.bookmarked.is_(True))
    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    stmt = stmt.where(or_(Video.derived_sort_date >= start, Video.derived_sort_date.is_(None))).order_by(Video.derived_sort_date.asc().nullslast(), Video.filename.asc())
    return db.execute(stmt.limit(1)).scalars().first()


def jump_to_position(db: Session, position: int, view: str = "unfinished") -> Video | None:
    if position < 1:
        return None
    stmt = select(Video).where(Video.is_missing.is_(False))
    if view == "unfinished":
        stmt = stmt.where(Video.review_state == "queued")
    elif view == "watched":
        stmt = stmt.where(Video.review_state == "watched")
    elif view == "skipped":
        stmt = stmt.where(Video.review_state == "skipped")
    elif view == "bookmarked":
        stmt = stmt.where(Video.bookmarked.is_(True))
    stmt = stmt.order_by(Video.derived_sort_date.asc().nullslast(), Video.filename.asc()).offset(position - 1).limit(1)
    return db.execute(stmt).scalars().first()


def dashboard_stats(db: Session) -> dict:
    settings = get_or_create_settings(db)
    total_videos = db.scalar(select(func.count()).select_from(Video).where(Video.is_missing.is_(False))) or 0
    unfinished_count = db.scalar(select(func.count()).select_from(Video).where(Video.review_state == "queued", Video.is_missing.is_(False))) or 0
    watched_count = db.scalar(select(func.count()).select_from(Video).where(Video.review_state == "watched", Video.is_missing.is_(False))) or 0
    skipped_count = db.scalar(select(func.count()).select_from(Video).where(Video.review_state == "skipped", Video.is_missing.is_(False))) or 0
    bookmarked_count = db.scalar(select(func.count()).select_from(Video).where(Video.bookmarked.is_(True), Video.is_missing.is_(False))) or 0
    continue_video = get_continue_video(db)
    current_position = None
    current_filename = None
    if settings.current_video_id:
        current_video = db.get(Video, settings.current_video_id)
        if current_video:
            current_filename = current_video.filename
            current_position, _ = get_queue_position(db, current_video.id, view="unfinished")
    return {"total_videos": total_videos, "unfinished_count": unfinished_count, "watched_count": watched_count, "skipped_count": skipped_count, "bookmarked_count": bookmarked_count, "current_video_id": settings.current_video_id, "current_queue_position": current_position, "queue_total": unfinished_count, "current_video_filename": current_filename, "continue_video_id": continue_video.id if continue_video else None, "continue_video_filename": continue_video.filename if continue_video else None}
