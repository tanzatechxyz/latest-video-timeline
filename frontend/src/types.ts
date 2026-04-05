export type ReviewState = 'queued' | 'watched' | 'skipped'

export interface SettingsResponse {
  root_folder: string
  supported_extensions: string[]
  watched_threshold_percent: number
  sort_priority: string[]
  auto_advance_on_done: boolean
  auto_advance_on_end: boolean
  generate_thumbnails: boolean
  thumbnail_interval_seconds: number
  thumbnail_width: number
  current_video_id: string | null
}

export interface VideoSummary {
  id: string
  filename: string
  rel_path: string
  extension: string
  size_bytes: number
  duration_seconds: number | null
  thumbnail_url: string | null
  derived_sort_date: string | null
  derived_sort_source: string | null
  discovered_at: string
  review_state: ReviewState
  bookmarked: boolean
  playback_position_seconds: number
  last_interaction_at: string | null
  is_missing: boolean
  error_message: string | null
}

export interface VideoDetail extends VideoSummary {
  abs_path: string
  filename_date: string | null
  metadata_date: string | null
  filesystem_date: string | null
  discovered_at: string
  last_seen_at: string
  watch_completed_at: string | null
  position_in_queue: number | null
  queue_total: number
  stream_url: string
}

export interface PaginatedVideosResponse {
  items: VideoSummary[]
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

export interface DashboardStatsResponse {
  total_videos: number
  unfinished_count: number
  watched_count: number
  skipped_count: number
  bookmarked_count: number
  current_video_id: string | null
  current_queue_position: number | null
  queue_total: number
  current_video_filename: string | null
  continue_video_id: string | null
  continue_video_filename: string | null
}

export interface QueueItemResponse { video: VideoDetail | null }
export interface QueueAdjacentResponse { previous_video_id: string | null; next_video_id: string | null }
export interface ScanStatusResponse { id: number | null; status: string; started_at: string | null; finished_at: string | null; total_files: number; scanned_files: number; added_files: number; updated_files: number; removed_files: number; renamed_files: number; error_count: number; message: string | null; error_details: string | null; is_running: boolean }
export interface PublicConfigResponse { auth_enabled: boolean }
