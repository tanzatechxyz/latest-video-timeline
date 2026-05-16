from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    auth_enabled: bool


class PublicConfigResponse(BaseModel):
    auth_enabled: bool


class SettingsResponse(BaseModel):
    root_folder: str
    supported_extensions: list[str]
    watched_threshold_percent: int
    sort_priority: list[str]
    auto_advance_on_done: bool
    auto_advance_on_end: bool
    generate_thumbnails: bool
    thumbnail_interval_seconds: int
    thumbnail_width: int
    current_video_id: str | None


class SettingsUpdateRequest(BaseModel):
    root_folder: Optional[str] = None
    supported_extensions: Optional[list[str]] = None
    watched_threshold_percent: Optional[int] = Field(default=None, ge=1, le=100)
    sort_priority: Optional[list[str]] = None
    auto_advance_on_done: Optional[bool] = None
    auto_advance_on_end: Optional[bool] = None
    generate_thumbnails: Optional[bool] = None
    thumbnail_interval_seconds: Optional[int] = Field(default=None, ge=1)
    thumbnail_width: Optional[int] = Field(default=None, ge=64)
    current_video_id: Optional[str] = None


class ScanStatusResponse(BaseModel):
    id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    total_files: int
    scanned_files: int
    added_files: int
    updated_files: int
    removed_files: int
    renamed_files: int
    error_count: int
    message: str | None
    error_details: str | None
    is_running: bool


class DashboardStatsResponse(BaseModel):
    total_videos: int
    unfinished_count: int
    watched_count: int
    skipped_count: int
    bookmarked_count: int
    current_video_id: str | None
    current_queue_position: int | None
    queue_total: int
    current_video_filename: str | None
    continue_video_id: str | None
    continue_video_filename: str | None


class VideoSummary(BaseModel):
    id: str
    filename: str
    rel_path: str
    extension: str
    size_bytes: int
    duration_seconds: float | None
    thumbnail_url: str | None
    derived_sort_date: datetime | None
    derived_sort_source: str | None
    modified_time: datetime | None
    discovered_at: datetime
    review_state: str
    bookmarked: bool
    playback_position_seconds: float
    last_interaction_at: datetime | None
    is_missing: bool
    error_message: str | None


class VideoDetail(VideoSummary):
    abs_path: str
    filename_date: datetime | None
    metadata_date: datetime | None
    filesystem_date: datetime | None
    discovered_at: datetime
    last_seen_at: datetime
    watch_completed_at: datetime | None
    position_in_queue: int | None
    queue_total: int
    stream_url: str


class PaginatedVideosResponse(BaseModel):
    items: list[VideoSummary]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class VideoStatusUpdateRequest(BaseModel):
    review_state: Optional[Literal["queued", "watched", "skipped"]] = None
    bookmarked: Optional[bool] = None
    playback_position_seconds: Optional[float] = Field(default=None, ge=0)
    current: Optional[bool] = None


class PlaybackUpdateRequest(BaseModel):
    position_seconds: float = Field(ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)
    event: Literal["progress", "pause", "ended", "unload", "load_error"] = "progress"
    current: bool = True


class ResumePlaybackResponse(BaseModel):
    video_id: str
    position_seconds: float


class QueueItemResponse(BaseModel):
    video: VideoDetail | None


class QueueAdjacentResponse(BaseModel):
    previous_video_id: str | None
    next_video_id: str | None


class QueueJumpResponse(BaseModel):
    video_id: str | None
