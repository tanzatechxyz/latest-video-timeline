from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from app.config import settings as env_settings
from app.db import SessionLocal
from app.models import ScanJob, Video
from app.services.settings_service import get_or_create_settings
from app.utils.dates import choose_sort_date, ensure_utc, parse_date_from_filename
from app.utils.ffprobe import generate_thumbnail, probe_video
from app.utils.files import content_fingerprint, filesystem_dates, path_fingerprint, root_entry_added_date

logger = logging.getLogger(__name__)


@dataclass
class RuntimeScanState:
    running: bool = False
    scan_job_id: int | None = None
    message: str | None = None


class ScanManager:
    def __init__(self) -> None:
        self.state = RuntimeScanState()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    async def start_scan(self) -> dict:
        async with self._lock:
            if self.state.running:
                return {"started": False, "reason": "scan already running", "scan_job_id": self.state.scan_job_id}
            self._task = asyncio.create_task(self._scan())
            return {"started": True}

    async def _scan(self) -> None:
        self.state.running = True
        db = SessionLocal()
        scan_job = None
        try:
            settings = get_or_create_settings(db)
            root_folder = Path(settings.root_folder)
            if not root_folder.exists() or not root_folder.is_dir():
                scan_job = ScanJob(status="failed", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), message=f"Root folder does not exist: {root_folder}")
                db.add(scan_job)
                db.commit()
                self.state.scan_job_id = scan_job.id
                self.state.message = scan_job.message
                return
            scan_job = ScanJob(status="running", started_at=datetime.now(timezone.utc), message="Scanning files")
            db.add(scan_job)
            db.commit(); db.refresh(scan_job)
            self.state.scan_job_id = scan_job.id
            extensions = {item.strip().lower() for item in settings.supported_extensions_csv.split(",") if item.strip()}
            all_files = []
            for current_root, _, filenames in os.walk(root_folder):
                for filename in filenames:
                    path = Path(current_root) / filename
                    if path.suffix.lower() in extensions:
                        all_files.append(path)
            scan_job.total_files = len(all_files)
            db.add(scan_job); db.commit()
            current_rel_paths = {str(path.relative_to(root_folder)) for path in all_files}
            existing_by_path = {video.rel_path: video for video in db.execute(select(Video)).scalars().all()}
            existing_by_fingerprint = {video.content_fingerprint: video for video in existing_by_path.values() if video.content_fingerprint}
            seen_rel_paths: set[str] = set()
            for idx, file_path in enumerate(sorted(all_files, key=lambda p: str(p).lower()), start=1):
                try:
                    rel_path = str(file_path.relative_to(root_folder))
                    seen_rel_paths.add(rel_path)
                    stat_result = file_path.stat()
                    birth_time, modified_time = filesystem_dates(stat_result)
                    filesystem_date = root_entry_added_date(root_folder, file_path)
                    current_by_path = existing_by_path.get(rel_path)
                    if current_by_path and current_by_path.size_bytes == stat_result.st_size and current_by_path.mtime_ns == stat_result.st_mtime_ns:
                        current_by_path.abs_path = str(file_path)
                        current_by_path.last_seen_at = datetime.now(timezone.utc)
                        current_by_path.is_missing = False
                        current_by_path.missing_since = None
                        sort_date, sort_source = choose_sort_date([item.strip() for item in settings.sort_priority_csv.split(",") if item.strip()], current_by_path.filename_date, current_by_path.metadata_date, filesystem_date)
                        if ensure_utc(current_by_path.filesystem_date) != filesystem_date or ensure_utc(current_by_path.derived_sort_date) != sort_date or current_by_path.derived_sort_source != sort_source:
                            current_by_path.birth_time = birth_time
                            current_by_path.modified_time = modified_time
                            current_by_path.filesystem_date = filesystem_date
                            current_by_path.derived_sort_date = sort_date
                            current_by_path.derived_sort_source = sort_source
                            scan_job.updated_files += 1
                        db.add(current_by_path)
                        scan_job.scanned_files = idx
                        db.add(scan_job); db.commit(); continue
                    file_content_fingerprint = content_fingerprint(file_path, stat_result.st_size)
                    file_path_fingerprint = path_fingerprint(rel_path)
                    fingerprint_match = existing_by_fingerprint.get(file_content_fingerprint) if file_content_fingerprint else None
                    rename_match = fingerprint_match if fingerprint_match and fingerprint_match.rel_path not in current_rel_paths else None
                    duration, metadata_date, probe_error = probe_video(file_path)
                    filename_date = parse_date_from_filename(file_path.name)
                    sort_date, sort_source = choose_sort_date([item.strip() for item in settings.sort_priority_csv.split(",") if item.strip()], filename_date, metadata_date, filesystem_date)
                    thumbnail_path = None; thumb_error = None
                    if settings.generate_thumbnails:
                        thumb_file = env_settings.thumbnails_path / ((file_content_fingerprint or file_path_fingerprint) + ".jpg")
                        thumb_error = generate_thumbnail(file_path, thumb_file, settings.thumbnail_interval_seconds, settings.thumbnail_width)
                        if thumb_error is None:
                            thumbnail_path = str(thumb_file)
                    video = current_by_path or rename_match
                    if video is None:
                        video_id_source = file_path_fingerprint if fingerprint_match else (file_content_fingerprint or file_path_fingerprint)
                        video = Video(id=f"vid_{video_id_source[:24]}", rel_path=rel_path, abs_path=str(file_path), filename=file_path.name, extension=file_path.suffix.lower(), size_bytes=stat_result.st_size, mtime_ns=stat_result.st_mtime_ns, birth_time=birth_time, modified_time=modified_time, discovered_at=datetime.now(timezone.utc), last_seen_at=datetime.now(timezone.utc), content_fingerprint=file_content_fingerprint, path_fingerprint=file_path_fingerprint, duration_seconds=duration, thumbnail_path=thumbnail_path, filename_date=filename_date, metadata_date=metadata_date, filesystem_date=filesystem_date, derived_sort_date=sort_date, derived_sort_source=sort_source, review_state="queued", bookmarked=False, playback_position_seconds=0.0, error_message=probe_error or thumb_error, is_missing=False)
                        db.add(video); scan_job.added_files += 1
                    else:
                        if rename_match and current_by_path is None and video.rel_path != rel_path:
                            scan_job.renamed_files += 1
                        video.rel_path = rel_path; video.abs_path = str(file_path); video.filename = file_path.name; video.extension = file_path.suffix.lower(); video.size_bytes = stat_result.st_size; video.mtime_ns = stat_result.st_mtime_ns; video.birth_time = birth_time; video.modified_time = modified_time; video.last_seen_at = datetime.now(timezone.utc); video.content_fingerprint = file_content_fingerprint; video.path_fingerprint = file_path_fingerprint; video.duration_seconds = duration if duration is not None else video.duration_seconds; video.thumbnail_path = thumbnail_path or video.thumbnail_path; video.filename_date = filename_date; video.metadata_date = metadata_date; video.filesystem_date = filesystem_date; video.derived_sort_date = sort_date; video.derived_sort_source = sort_source; video.error_message = probe_error or thumb_error; video.is_missing = False; video.missing_since = None
                        db.add(video); scan_job.updated_files += 1
                    existing_by_path[rel_path] = video
                    if file_content_fingerprint:
                        existing_by_fingerprint[file_content_fingerprint] = video
                except Exception as exc:
                    logger.exception("Failed to scan file %s", file_path)
                    scan_job.error_count += 1
                    details = [scan_job.error_details] if scan_job.error_details else []
                    details.append(f"{file_path}: {exc}")
                    scan_job.error_details = "\n".join([item for item in details if item][-20:])
                finally:
                    scan_job.scanned_files = idx
                    db.add(scan_job); db.commit()
            for video in db.execute(select(Video)).scalars().all():
                if video.rel_path not in seen_rel_paths and not video.is_missing:
                    video.is_missing = True; video.missing_since = datetime.now(timezone.utc); db.add(video); scan_job.removed_files += 1
            scan_job.status = "finished"; scan_job.finished_at = datetime.now(timezone.utc); scan_job.message = "Scan complete"
            db.add(scan_job); db.commit()
        except Exception as exc:
            logger.exception("Scan failed")
            if scan_job is None:
                scan_job = ScanJob(status="failed", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), message=str(exc), error_details=str(exc))
                db.add(scan_job)
            else:
                scan_job.status = "failed"; scan_job.finished_at = datetime.now(timezone.utc); scan_job.message = "Scan failed"; scan_job.error_details = (scan_job.error_details or "") + f"\n{exc}"; db.add(scan_job)
            db.commit()
        finally:
            db.close(); self.state.running = False; self.state.message = None

    def latest_status(self) -> dict:
        db = SessionLocal()
        try:
            latest = db.execute(select(ScanJob).order_by(ScanJob.id.desc()).limit(1)).scalars().first()
            if latest is None:
                return {"id": None, "status": "idle", "started_at": None, "finished_at": None, "total_files": 0, "scanned_files": 0, "added_files": 0, "updated_files": 0, "removed_files": 0, "renamed_files": 0, "error_count": 0, "message": None, "error_details": None, "is_running": self.state.running}
            return {"id": latest.id, "status": latest.status, "started_at": latest.started_at, "finished_at": latest.finished_at, "total_files": latest.total_files, "scanned_files": latest.scanned_files, "added_files": latest.added_files, "updated_files": latest.updated_files, "removed_files": latest.removed_files, "renamed_files": latest.renamed_files, "error_count": latest.error_count, "message": latest.message, "error_details": latest.error_details, "is_running": self.state.running}
        finally:
            db.close()


scan_manager = ScanManager()
