from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path


def utc_from_timestamp(value: float | None) -> datetime | None:
    return datetime.fromtimestamp(value, tz=timezone.utc) if value is not None else None


def filesystem_dates(stat_result: os.stat_result) -> tuple[datetime | None, datetime]:
    birth_ts = getattr(stat_result, "st_birthtime", None)
    birth_time = utc_from_timestamp(birth_ts) if birth_ts else None
    modified_time = utc_from_timestamp(stat_result.st_mtime) or datetime.now(timezone.utc)
    return birth_time, modified_time


def root_entry_added_date(root_folder: Path, file_path: Path) -> datetime:
    try:
        relative = file_path.relative_to(root_folder)
        entry_path = root_folder / relative.parts[0] if relative.parts else file_path
        stat_result = entry_path.stat()
    except (OSError, ValueError):
        stat_result = file_path.stat()
    birth_ts = getattr(stat_result, "st_birthtime", None)
    for timestamp in (birth_ts, stat_result.st_ctime, stat_result.st_mtime):
        value = utc_from_timestamp(timestamp)
        if value is not None:
            return value
    return datetime.now(timezone.utc)


def path_fingerprint(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()


def content_fingerprint(file_path: Path, size_bytes: int, sample_size: int = 262_144) -> str | None:
    try:
        sha1 = hashlib.sha1()
        sha1.update(str(size_bytes).encode("utf-8"))
        with file_path.open("rb") as handle:
            sha1.update(handle.read(sample_size))
            if size_bytes > sample_size:
                handle.seek(max(size_bytes - sample_size, 0))
                sha1.update(handle.read(sample_size))
        return sha1.hexdigest()
    except OSError:
        return None
