"""
BugHunter — FastAPI Application
REST API + Server-Sent Events for real-time scan progress.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

# Ensure project root is in sys.path so backend package can always be found
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.agent.orchestrator import ScanOrchestrator
from backend.config import get_settings
from backend.db.database import BugHunterDB
from backend.models import ScanConfig
from backend.services.url_validator import URLValidationError, validate_scan_url

logger = logging.getLogger(__name__)

# Global instances
_db: BugHunterDB | None = None
_orchestrator: ScanOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — initialize and cleanup resources."""
    global _db, _orchestrator

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Initialize database
    _db = BugHunterDB(db_path=settings.db_path)
    await _db.initialize()

    # Initialize orchestrator
    _orchestrator = ScanOrchestrator(db=_db)

    logger.info("BugHunter backend started on %s:%d", settings.host, settings.port)
    yield

    logger.info("BugHunter backend shutting down")


app = FastAPI(
    title="BugHunter API",
    description="Autonomous AI-powered web testing agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins + ["*"],  # Configurable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "demo_mode": get_settings().demo_mode,
        "llm_provider": get_settings().llm_provider,
    }


# ── Scans ─────────────────────────────────────────────────────────────────────


class StartScanRequest(BaseModel):
    url: str
    max_depth: int = 3
    browser: str = "chromium"
    headless: bool = True
    enable_a11y: bool = True
    enable_visual_diff: bool = False
    enable_exploration: bool = True
    max_actions: int = 50
    llm_provider: str | None = None


@app.post("/api/scans")
async def start_scan(request: StartScanRequest) -> dict:
    """Start a new autonomous scan."""
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    settings = get_settings()
    try:
        validate_scan_url(request.url, demo_mode=settings.demo_mode)
    except URLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config = ScanConfig(
        url=request.url,
        max_depth=request.max_depth,
        browser=request.browser,
        headless=request.headless,
        enable_a11y=request.enable_a11y,
        enable_visual_diff=request.enable_visual_diff,
        enable_exploration=request.enable_exploration,
        max_actions=request.max_actions,
        llm_provider=request.llm_provider,
    )

    try:
        scan_id = await _orchestrator.start_scan(config)
        return {"scan_id": scan_id, "status": "started", "url": request.url}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to start scan")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/scans")
async def list_scans(limit: int = 50) -> dict:
    """List recent scans."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    scans = await _db.list_scans(limit=limit)
    return {"scans": scans, "total": len(scans)}


@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict:
    """Get scan details by id."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    scan = await _db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return scan


@app.get("/api/scans/{scan_id}/findings")
async def get_findings(scan_id: str) -> dict:
    """Get all findings for a scan."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    findings = await _db.get_findings(scan_id)
    return {"findings": findings, "total": len(findings)}


@app.get("/api/scans/{scan_id}/stream")
async def stream_scan_events(scan_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream for real-time scan progress.
    Connect to this endpoint to receive live updates during a scan.
    """
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    async def event_generator() -> AsyncIterator[str]:
        queue = _orchestrator.get_event_queue(scan_id)
        if queue is None:
            # No active queue — check if scan exists in DB
            if _db:
                scan = await _db.get_scan(scan_id)
                if scan:
                    yield f"data: {json.dumps({'type': 'scan_status', 'status': scan['status']})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Scan not found'})}\n\n"
            return

        # Stream events until scan completes
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"

                # Stop streaming when scan ends
                if event.get("type") in ("completed", "failed", "cancelled"):
                    break
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield ": keepalive\n\n"
            except Exception as exc:
                logger.warning("SSE stream error for %s: %s", scan_id, exc)
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── Reports ───────────────────────────────────────────────────────────────────


@app.get("/api/scans/{scan_id}/report", response_model=None)
async def get_report(scan_id: str, format: str = "json") -> JSONResponse | FileResponse:
    """Download a scan report."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    scan = await _db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if format == "html":
        html_path = scan.get("report_html_path")
        if html_path and Path(html_path).exists():
            return FileResponse(html_path, media_type="text/html")
        raise HTTPException(status_code=404, detail="HTML report not available yet")

    json_path = scan.get("report_json_path")
    if json_path and Path(json_path).exists():
        return FileResponse(json_path, media_type="application/json")

    # Return scan data as JSON if no report file
    findings = await _db.get_findings(scan_id)
    return JSONResponse({
        "scan": scan,
        "findings": findings,
    })


# ── Screenshots ───────────────────────────────────────────────────────────────


@app.get("/api/screenshots/{scan_id}/{filename}")
async def get_screenshot(scan_id: str, filename: str) -> FileResponse:
    """Serve a screenshot file."""
    settings = get_settings()
    path = Path(settings.reports_dir) / scan_id / "screenshots" / filename
    if not path.exists():
        # Try without screenshots subfolder
        path = Path(settings.reports_dir) / scan_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path, media_type="image/png")


# ── URL Validation ────────────────────────────────────────────────────────────


@app.post("/api/validate-url")
async def validate_url_endpoint(body: dict) -> dict:
    """Validate a URL before submitting a scan."""
    url = body.get("url", "")
    settings = get_settings()
    try:
        validated = validate_scan_url(url, demo_mode=settings.demo_mode)
        return {"valid": True, "url": validated}
    except URLValidationError as exc:
        return {"valid": False, "error": str(exc)}


# ── Frontend static files (served in production) ──────────────────────────────

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (_FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str, request: Request) -> HTMLResponse:
    """Serve React frontend SPA."""
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>BugHunter</h1><p>Frontend not built. Run: cd frontend && npm run build</p>")


if __name__ == "__main__":
    import uvicorn
    cfg = get_settings()
    uvicorn.run("backend.main:app", host=cfg.host, port=cfg.port, reload=True)
