from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.auth import maybe_require_auth
from app.db import get_db
from app.models import Video
from app.schemas import PaginatedVideosResponse, PlaybackUpdateRequest, ResumePlaybackResponse, VideoDetail, VideoStatusUpdateRequest, VideoSummary
from app.services.queue_service import get_queue_position, set_current_video
from app.services.settings_service import get_or_create_settings

router = APIRouter(prefix="/api/videos", tags=["videos"], dependencies=[Depends(maybe_require_auth)])


def to_summary(video: Video, request: Request) -> VideoSummary:
    thumb_url = f"{request.base_url}api/videos/{video.id}/thumbnail" if video.thumbnail_path else None
    return VideoSummary(id=video.id, filename=video.filename, rel_path=video.rel_path, extension=video.extension, size_bytes=video.size_bytes, duration_seconds=video.duration_seconds, thumbnail_url=thumb_url, derived_sort_date=video.derived_sort_date, derived_sort_source=video.derived_sort_source, discovered_at=video.discovered_at, review_state=video.review_state, bookmarked=video.bookmarked, playback_position_seconds=video.playback_position_seconds, last_interaction_at=video.last_interaction_at, is_missing=video.is_missing, error_message=video.error_message)


def to_detail(video: Video, request: Request, view: str = "unfinished") -> VideoDetail:
    position_in_queue, queue_total = get_queue_position(request.state.db, video.id, view=view)
    base = to_summary(video, request)
    return VideoDetail(**base.model_dump(), abs_path=video.abs_path, filename_date=video.filename_date, metadata_date=video.metadata_date, filesystem_date=video.filesystem_date, discovered_at=video.discovered_at, last_seen_at=video.last_seen_at, watch_completed_at=video.watch_completed_at, position_in_queue=position_in_queue, queue_total=queue_total, stream_url=f"{request.base_url}api/videos/{video.id}/stream")


@router.get("", response_model=PaginatedVideosResponse)
def list_videos(request: Request, view: str = Query(default="unfinished", pattern="^(all|unfinished|watched|skipped|bookmarked)$"), sort: str = Query(default="chronological", pattern="^(chronological|latest_added)$"), year: int | None = None, month: int | None = Query(default=None, ge=1, le=12), page: int = Query(default=1, ge=1), page_size: int = Query(default=60, ge=1, le=250), search: str | None = None, db: Session = Depends(get_db)) -> PaginatedVideosResponse:
    request.state.db = db
    stmt = select(Video).where(Video.is_missing.is_(False))
    if view == "unfinished": stmt = stmt.where(Video.review_state == "queued")
    elif view == "watched": stmt = stmt.where(Video.review_state == "watched")
    elif view == "skipped": stmt = stmt.where(Video.review_state == "skipped")
    elif view == "bookmarked": stmt = stmt.where(Video.bookmarked.is_(True))
    if year is not None: stmt = stmt.where(func.strftime("%Y", Video.derived_sort_date) == f"{year:04d}")
    if month is not None: stmt = stmt.where(func.strftime("%m", Video.derived_sort_date) == f"{month:02d}")
    if search: stmt = stmt.where(Video.filename.ilike(f"%{search}%"))
    if sort == "latest_added":
        stmt = stmt.order_by(Video.discovered_at.desc(), Video.filename.asc())
    else:
        stmt = stmt.order_by(Video.derived_sort_date.asc().nullslast(), Video.filename.asc())
    total_items = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    total_pages = max((total_items + page_size - 1) // page_size, 1)
    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return PaginatedVideosResponse(items=[to_summary(video, request) for video in items], page=page, page_size=page_size, total_items=total_items, total_pages=total_pages)


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(video_id: str, request: Request, view: str = "unfinished", db: Session = Depends(get_db)) -> VideoDetail:
    request.state.db = db
    video = db.get(Video, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    return to_detail(video, request, view=view)


@router.get("/{video_id}/stream")
def stream_video(video_id: str, db: Session = Depends(get_db)) -> FileResponse:
    video = db.get(Video, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    path = Path(video.abs_path)
    if video.is_missing or not path.exists(): raise HTTPException(status_code=404, detail="Video file is missing")
    media_map = {'.mp4':'video/mp4','.webm':'video/webm','.mkv':'video/x-matroska','.mov':'video/quicktime','.m4v':'video/x-m4v'}
    return FileResponse(path=path, media_type=media_map.get(video.extension, 'application/octet-stream'), filename=video.filename)


@router.get("/{video_id}/thumbnail")
def thumbnail(video_id: str, db: Session = Depends(get_db)) -> FileResponse:
    video = db.get(Video, video_id)
    if not video or not video.thumbnail_path: raise HTTPException(status_code=404, detail="Thumbnail not found")
    path = Path(video.thumbnail_path)
    if not path.exists(): raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(path=path, media_type="image/jpeg")


@router.post("/{video_id}/status", response_model=VideoDetail)
def update_status(video_id: str, payload: VideoStatusUpdateRequest, request: Request, db: Session = Depends(get_db)) -> VideoDetail:
    request.state.db = db
    video = db.get(Video, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    if payload.review_state is not None:
        video.review_state = payload.review_state
        if payload.review_state == "watched":
            video.watch_completed_at = datetime.now(timezone.utc)
            video.playback_position_seconds = video.duration_seconds or video.playback_position_seconds
    if payload.bookmarked is not None: video.bookmarked = payload.bookmarked
    if payload.playback_position_seconds is not None: video.playback_position_seconds = payload.playback_position_seconds
    video.last_interaction_at = datetime.now(timezone.utc)
    if payload.current:
        set_current_video(db, video.id)
    elif payload.review_state in {"watched", "skipped"}:
        current_settings = get_or_create_settings(db)
        if current_settings.current_video_id == video.id:
            current_settings.current_video_id = None; db.add(current_settings)
    db.add(video); db.commit(); db.refresh(video)
    return to_detail(video, request)


@router.post("/{video_id}/playback", response_model=ResumePlaybackResponse)
def update_playback(video_id: str, payload: PlaybackUpdateRequest, db: Session = Depends(get_db)) -> ResumePlaybackResponse:
    video = db.get(Video, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    settings = get_or_create_settings(db)
    video.playback_position_seconds = payload.position_seconds
    video.last_interaction_at = datetime.now(timezone.utc)
    if payload.current: settings.current_video_id = video.id; db.add(settings)
    if payload.event == "ended":
        video.playback_position_seconds = 0.0 if settings.auto_advance_on_end else payload.position_seconds
        if settings.auto_advance_on_end:
            video.review_state = "watched"; video.watch_completed_at = datetime.now(timezone.utc); settings.current_video_id = None; db.add(settings)
    elif payload.event != "load_error" and payload.duration_seconds:
        watched_percent = (payload.position_seconds / payload.duration_seconds) * 100 if payload.duration_seconds else 0
        if watched_percent >= settings.watched_threshold_percent:
            video.review_state = "watched"; video.watch_completed_at = datetime.now(timezone.utc)
    db.add(video); db.commit()
    return ResumePlaybackResponse(video_id=video.id, position_seconds=video.playback_position_seconds)


@router.get("/{video_id}/resume", response_model=ResumePlaybackResponse)
def resume_playback(video_id: str, db: Session = Depends(get_db)) -> ResumePlaybackResponse:
    video = db.get(Video, video_id)
    if not video: raise HTTPException(status_code=404, detail="Video not found")
    return ResumePlaybackResponse(video_id=video.id, position_seconds=video.playback_position_seconds)
