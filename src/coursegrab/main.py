"""FastAPI application for CourseGrab."""

import asyncio
import json
import logging
import webbrowser
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import StreamingResponse

from coursegrab.downloader import (
    DownloadJob,
    DownloadOptions,
    extract_slug,
    run_download,
    validate_options,
)

# Mask CAUTH in logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(title="CourseGrab")

STATIC_DIR = Path(__file__).parent / "static"

# Track active download jobs by a simple counter
_jobs: dict[int, DownloadJob] = {}
_job_counter = 0


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the main UI."""
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.post("/api/validate")
async def api_validate(request: Request) -> JSONResponse:
    """Validate download options before starting."""
    data = await request.json()
    options = _parse_options(data)
    errors = validate_options(options)
    if errors:
        return JSONResponse({"ok": False, "errors": errors})

    slug = extract_slug(options.url)
    return JSONResponse({"ok": True, "slug": slug, "errors": []})


@app.post("/api/download")
async def api_download(request: Request) -> StreamingResponse:
    """Start download and stream logs via SSE."""
    global _job_counter
    data = await request.json()
    options = _parse_options(data)

    _job_counter += 1
    job_id = _job_counter
    job = DownloadJob()
    _jobs[job_id] = job

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # Send job_id so client can cancel
            yield _sse_event({"type": "started", "job_id": job_id})

            async for line in run_download(options, job):
                yield _sse_event({"type": "log", "message": line})
                await asyncio.sleep(0)  # yield control

            yield _sse_event({"type": "done"})
        finally:
            _jobs.pop(job_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/cancel/{job_id}")
async def api_cancel(job_id: int) -> JSONResponse:
    """Cancel a running download job."""
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse({"ok": False, "error": "Job not found"}, status_code=404)

    job.cancelled = True
    if job.process:
        job.process.terminate()
    return JSONResponse({"ok": True})


@app.get("/api/default-output")
async def api_default_output() -> JSONResponse:
    """Return the default output directory."""
    default = Path.home() / "Downloads" / "coursera"
    return JSONResponse({"path": str(default)})


@app.get("/api/browse-folder")
async def api_browse_folder(start: str = "") -> JSONResponse:
    """Open a native folder picker dialog and return the selected path."""
    import threading

    result: dict[str, str] = {}

    def _pick() -> None:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial = start if start and Path(start).is_dir() else str(Path.home())
        chosen = filedialog.askdirectory(initialdir=initial, title="Select output folder")
        root.destroy()
        if chosen:
            result["path"] = chosen

    thread = threading.Thread(target=_pick)
    thread.start()
    thread.join(timeout=120)

    if "path" in result:
        return JSONResponse({"path": result["path"]})
    return JSONResponse({"path": ""})


def _parse_options(data: dict) -> DownloadOptions:
    """Parse JSON request body into DownloadOptions."""
    return DownloadOptions(
        url=str(data.get("url", "")),
        output_dir=str(
            data.get("output_dir", str(Path.home() / "Downloads" / "coursera"))
        ),
        cauth=str(data.get("cauth", "")),
        video=bool(data.get("video", True)),
        video_resolution=str(data.get("video_resolution", "720p")),
        subtitles=bool(data.get("subtitles", True)),
        subtitle_languages=str(data.get("subtitle_languages", "en,pl")),
        slides_pdf=bool(data.get("slides_pdf", True)),
        slides_pptx=bool(data.get("slides_pptx", True)),
        download_notebooks=bool(data.get("download_notebooks", False)),
        download_quizzes=bool(data.get("download_quizzes", False)),
        parallel_jobs=int(data.get("parallel_jobs", 4)),
    )


def _sse_event(data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


def cli() -> None:
    """CLI entry point — start the server and open browser."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    host = "127.0.0.1"
    port = 8000
    logger.info(f"Starting CourseGrab at http://{host}:{port}")
    webbrowser.open(f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli()
