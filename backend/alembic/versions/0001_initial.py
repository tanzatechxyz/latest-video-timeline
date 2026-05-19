"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("root_folder", sa.String(length=1024), nullable=False),
        sa.Column("supported_extensions_csv", sa.String(length=512), nullable=False),
        sa.Column("watched_threshold_percent", sa.Integer(), nullable=False),
        sa.Column("sort_priority_csv", sa.String(length=128), nullable=False),
        sa.Column("auto_advance_on_done", sa.Boolean(), nullable=False),
        sa.Column("auto_advance_on_end", sa.Boolean(), nullable=False),
        sa.Column("generate_thumbnails", sa.Boolean(), nullable=False),
        sa.Column("thumbnail_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("thumbnail_width", sa.Integer(), nullable=False),
        sa.Column("current_video_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("scanned_files", sa.Integer(), nullable=False),
        sa.Column("added_files", sa.Integer(), nullable=False),
        sa.Column("updated_files", sa.Integer(), nullable=False),
        sa.Column("removed_files", sa.Integer(), nullable=False),
        sa.Column("renamed_files", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "videos",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("rel_path", sa.String(length=2048), nullable=False),
        sa.Column("abs_path", sa.String(length=4096), nullable=False),
        sa.Column("filename", sa.String(length=1024), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mtime_ns", sa.BigInteger(), nullable=False),
        sa.Column("birth_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modified_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("path_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=4096), nullable=True),
        sa.Column("filename_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filesystem_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("derived_sort_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("derived_sort_source", sa.String(length=32), nullable=True),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column("bookmarked", sa.Boolean(), nullable=False),
        sa.Column("playback_position_seconds", sa.Float(), nullable=False),
        sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("watch_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_missing", sa.Boolean(), nullable=False),
        sa.Column("missing_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rel_path", name="uq_videos_rel_path"),
    )
    op.create_index("ix_videos_content_fingerprint", "videos", ["content_fingerprint"])
    op.create_index("ix_videos_derived_sort_date", "videos", ["derived_sort_date"])
    op.create_index("ix_videos_review_state", "videos", ["review_state"])
    op.create_index("ix_videos_bookmarked", "videos", ["bookmarked"])
    op.create_index("ix_videos_is_missing", "videos", ["is_missing"])
    op.execute("""
        INSERT INTO app_settings (
            id, root_folder, supported_extensions_csv, watched_threshold_percent,
            sort_priority_csv, auto_advance_on_done, auto_advance_on_end,
            generate_thumbnails, thumbnail_interval_seconds, thumbnail_width,
            current_video_id, created_at, updated_at
        ) VALUES (
            1, '/videos', '.mp4,.mov,.m4v,.webm,.mkv', 95,
            'filesystem,filename,metadata', 1, 1,
            0, 3, 480,
            NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
    """)


def downgrade() -> None:
    op.drop_index("ix_videos_is_missing", table_name="videos")
    op.drop_index("ix_videos_bookmarked", table_name="videos")
    op.drop_index("ix_videos_review_state", table_name="videos")
    op.drop_index("ix_videos_derived_sort_date", table_name="videos")
    op.drop_index("ix_videos_content_fingerprint", table_name="videos")
    op.drop_table("videos")
    op.drop_table("scan_jobs")
    op.drop_table("app_settings")
