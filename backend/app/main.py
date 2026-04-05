from __future__ import annotations

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api import auth, dashboard, queue, scan, settings, videos
from app.config import settings as env_settings
from app.db import SessionLocal
from app.services.scan_service import scan_manager
from app.services.settings_service import get_or_create_settings

app = FastAPI(title="Latest Review Queue", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=env_settings.cors_origins_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(scan.router)
app.include_router(settings.router)
app.include_router(videos.router)
app.include_router(queue.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    env_settings.data_path.mkdir(parents=True, exist_ok=True)
    env_settings.thumbnails_path.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        get_or_create_settings(db)
    finally:
        db.close()
    if env_settings.auto_scan_on_startup:
        asyncio.create_task(scan_manager.start_scan())


frontend_build = env_settings.frontend_build_path
if frontend_build.exists():
    assets_dir = frontend_build / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        target = frontend_build / full_path
        if full_path and target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_build / "index.html")
