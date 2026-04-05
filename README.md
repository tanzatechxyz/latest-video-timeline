# Latest Review Queue

A self-hosted, browser-based review app for reviewing the newest added items first, while still preserving chronological queue tools.

This project started as a customized copy of `review-queue-project` and is tuned to make recent additions easy to spot and open immediately.

Core behavior:

- scan a folder of thousands of videos
- keep the original chronological queue behavior
- surface the newest discovered items as a **Latest review** section
- allow timeline sorting by `chronological` or `latest_added`
- remember exactly where you left off across sessions
- stay fast and tablet-friendly on a local network

## Stack

- **Backend:** FastAPI
- **Frontend:** React + TypeScript + Vite
- **Database:** SQLite
- **Streaming:** files remain on disk and are streamed directly
- **Background work:** asynchronous folder scans

## Repository layout

```text
.
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   └── utils/
│   └── scripts/
├── frontend/
├── docker/
├── docs/
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Main behavior

### Continue flow

1. Open the app.
2. Tap **Continue**.
3. The backend returns the exact current item if it is still unfinished, otherwise the oldest unfinished item.
4. Playback resumes from the saved position.
5. When the item is done, the app can auto-advance.

## Progress persistence

Progress is stored in SQLite, not only in browser storage.

For each video the app stores:

- review state (`queued`, `watched`, `skipped`)
- bookmark flag
- last playback position
- last interaction timestamp
- watch completion timestamp

For the app it stores:

- `current_video_id`

See also [`docs/progress-persistence.md`](docs/progress-persistence.md).

## Chronological sort strategy

The app stores multiple candidate dates per file and computes a final sort date using configurable priority.

Default priority:

1. filename date
2. embedded metadata date
3. filesystem date

The selected value is stored as:

- `derived_sort_date`
- `derived_sort_source`

See also [`docs/sort-order.md`](docs/sort-order.md).

## Sensible defaults

- root folder: `/videos`
- app data directory: `/data`
- DB path: `/data/review_queue.db`
- watched threshold: `95%`
- sort priority: `filename,metadata,filesystem`
- auto advance after Done: `true`
- auto advance on ended: `true`
- thumbnails: `false`
- auth: `false`

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export APP_DB_PATH=$PWD/../data/review_queue.db
export APP_ROOT_FOLDER=$PWD/../sample-videos
alembic upgrade head
uvicorn app.main:app --reload --port 8080
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8080`.

## Quick Docker run

1. Put some local videos in `./sample-videos`
2. Create `./data`
3. Build and start

```bash
docker compose up --build
```

App URL:

```text
http://localhost:8080
```

## Sample seed / dev mode

If you want to point the app at a local folder full of test videos:

```bash
cd backend
source .venv/bin/activate
python scripts/dev_seed_from_folder.py /absolute/path/to/test/videos
```

## Scanning / indexing details

### What is indexed

- relative path
- absolute path
- filename
- extension
- size
- duration when `ffprobe` is available
- filename date when parseable
- metadata date when available
- filesystem date
- derived sort date and source
- thumbnail path when enabled
- review state and playback progress

### Rename handling

The scanner prefers a content-based fingerprint:

- `sha1(size + first chunk + last chunk)`

If a path changes but the fingerprint matches an existing row, the app updates the path without losing progress.

### Removed files

Missing files are not immediately deleted from the database.
They are marked `is_missing = true`, which preserves historical progress and avoids corrupting the queue.

## API overview

### Scan

- `GET /api/scan/status`
- `POST /api/scan/start`

### Dashboard

- `GET /api/dashboard/stats`

### Videos

- `GET /api/videos`
- `GET /api/videos/{id}`
- `GET /api/videos/{id}/stream`
- `GET /api/videos/{id}/thumbnail`
- `POST /api/videos/{id}/status`
- `POST /api/videos/{id}/playback`
- `GET /api/videos/{id}/resume`

### Queue

- `GET /api/queue/current`
- `GET /api/queue/continue`
- `GET /api/queue/adjacent/{id}`
- `GET /api/queue/jump?jump_date=YYYY-MM-DD`
- `GET /api/queue/jump?position=917`

### Settings

- `GET /api/settings`
- `PUT /api/settings`

### Auth

- `GET /api/auth/public-config`
- `POST /api/auth/login`

## SQLite schema and migrations

Alembic manages the database schema.

Initial migration:

- `backend/alembic/versions/0001_initial.py`

Schema notes:

- `videos` stores indexed file data and progress
- `app_settings` stores singleton app behavior and current anchor item
- `scan_jobs` stores scan history and progress counters

See [`docs/database-schema.md`](docs/database-schema.md).

## Optional metadata and thumbnails

- If `ffprobe` is available, duration and metadata dates are extracted.
- If `ffmpeg` is available and thumbnail generation is enabled, thumbnails are generated into `/data/thumbnails`.
- If either tool is unavailable, the app still works and falls back gracefully.

## TrueNAS SCALE deployment notes

TrueNAS SCALE documentation indicates that current 24.10+ releases support custom apps using Docker images and also offer an advanced YAML screen for Docker Compose syntax, while older 24.04 guidance used Kubernetes-backed custom apps. The safest production approach for this project is to run it as a Docker-based custom app on 24.10+ with two bind mounts: one read-only mount for the media dataset and one read-write mount for app data.

### Recommended TrueNAS mounts

- media dataset → `/videos` (read-only)
- app data dataset → `/data` (read-write)

### Recommended environment variables

```text
APP_DB_PATH=/data/review_queue.db
APP_ROOT_FOLDER=/videos
APP_DATA_DIR=/data
APP_WATCHED_THRESHOLD_PERCENT=95
APP_SORT_PRIORITY=filename,metadata,filesystem
APP_AUTO_ADVANCE_ON_DONE=true
APP_AUTO_ADVANCE_ON_END=true
APP_GENERATE_THUMBNAILS=false
APP_AUTH_ENABLED=true
APP_USERNAME=admin
APP_PASSWORD=choose-a-strong-local-password
APP_SECRET_KEY=replace-with-a-long-random-secret
```

### Docker image deployment on TrueNAS SCALE

If you build the image from this source elsewhere and push it to a registry, use a custom app pointing to that image. Mount the datasets above and expose container port `8080`.

### YAML / Compose style deployment

The current TrueNAS UI documentation also describes an advanced YAML workflow for custom apps using Docker Compose syntax. That is suitable when you prefer managing bind mounts and ports in a Compose-like file instead of the guided wizard.

Example service definition:

```yaml
services:
  instagram-review-queue:
    image: your-registry/instagram-review-queue:latest
    container_name: instagram-review-queue
    ports:
      - "8080:8080"
    environment:
      APP_DB_PATH: /data/review_queue.db
      APP_ROOT_FOLDER: /videos
      APP_DATA_DIR: /data
      APP_WATCHED_THRESHOLD_PERCENT: "95"
      APP_SORT_PRIORITY: filename,metadata,filesystem
      APP_AUTO_ADVANCE_ON_DONE: "true"
      APP_AUTO_ADVANCE_ON_END: "true"
      APP_GENERATE_THUMBNAILS: "false"
      APP_AUTH_ENABLED: "true"
      APP_USERNAME: admin
      APP_PASSWORD: choose-a-strong-local-password
      APP_SECRET_KEY: replace-with-a-long-random-secret
    volumes:
      - /mnt/POOL/media/instagram:/videos:ro
      - /mnt/POOL/appdata/instagram-review-queue:/data
    restart: unless-stopped
```

## Reliability notes

- unchanged files are skipped during scan
- scanning runs in the background
- large views are paginated
- missing or corrupt files are surfaced with clear errors
- video files are streamed directly, not duplicated into app storage
- queue state survives restarts because it lives in SQLite

## UX notes

This project intentionally avoids Plex/Jellyfin style patterns.

Primary bias:

- Continue first
- minimal clutter
- large buttons
- one-hand tablet use
- fast navigation through a chronological queue
