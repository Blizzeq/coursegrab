"""FastAPI application for CourseGrab."""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import webbrowser
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from coursegrab.downloader import (
    DownloadJob,
    DownloadOptions,
    extract_slug,
    run_download,
    validate_options,
)
from coursegrab.zipper import create_zip_archive

# Mask CAUTH in logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(title="CourseGrab")

STATIC_DIR = Path(__file__).parent / "static"
IS_VERCEL = bool(os.environ.get("VERCEL"))

# Track active download jobs by a simple counter
_jobs: dict[int, DownloadJob] = {}
_job_counter = 0

# Track ZIP files ready for download
_zip_files: dict[int, Path] = {}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the main UI."""
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/config")
async def api_config() -> JSONResponse:
    """Return runtime configuration for the frontend."""
    return JSONResponse({"vercel": IS_VERCEL})


@app.post("/api/validate")
async def api_validate(request: Request) -> JSONResponse:
    """Validate download options before starting."""
    data = await request.json()
    options = _parse_options(data)
    errors = validate_options(options, skip_output_validation=IS_VERCEL)
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

    # On Vercel, override output to temp directory and force sequential
    # downloads (Lambda lacks /dev/shm required by multiprocessing.Pool)
    tmp_dir = None
    if IS_VERCEL:
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"coursegrab_{job_id}_"))
        options.output_dir = str(tmp_dir)
        options.parallel_jobs = 1

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            yield _sse_event({"type": "started", "job_id": job_id})

            async for line in run_download(
                options, job, skip_output_validation=IS_VERCEL
            ):
                yield _sse_event({"type": "log", "message": line})
                await asyncio.sleep(0)

            # On Vercel, create ZIP after download completes
            if IS_VERCEL and tmp_dir and not job.cancelled:
                yield _sse_event({"type": "log", "message": "Creating ZIP archive..."})
                slug = extract_slug(options.url) or "course"
                zip_path = Path(tempfile.gettempdir()) / f"{slug}_{job_id}.zip"
                file_count, total_bytes = await create_zip_archive(tmp_dir, zip_path)

                if file_count > 0:
                    _zip_files[job_id] = zip_path
                    size_mb = round(total_bytes / 1024 / 1024, 1)
                    yield _sse_event(
                        {
                            "type": "zip_ready",
                            "job_id": job_id,
                            "filename": f"{slug}.zip",
                            "file_count": file_count,
                            "size_mb": size_mb,
                        }
                    )
                else:
                    yield _sse_event(
                        {
                            "type": "log",
                            "message": "No files were downloaded.",
                        }
                    )

            yield _sse_event({"type": "done"})
        finally:
            _jobs.pop(job_id, None)
            # Clean up temp download dir (ZIP stays for retrieval)
            if tmp_dir and tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/download/{job_id}/zip", response_model=None)
async def api_download_zip(job_id: int) -> FileResponse | JSONResponse:
    """Serve the ZIP file for a completed download."""
    zip_path = _zip_files.get(job_id)
    if not zip_path or not zip_path.exists():
        return JSONResponse({"error": "ZIP not found"}, status_code=404)

    filename = zip_path.stem.rsplit("_", 1)[0] + ".zip"

    def cleanup() -> None:
        _zip_files.pop(job_id, None)
        zip_path.unlink(missing_ok=True)

    return FileResponse(
        path=str(zip_path),
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(cleanup),
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
    if IS_VERCEL:
        return JSONResponse({"path": ""})
    default = Path.home() / "Downloads" / "coursera"
    return JSONResponse({"path": str(default)})


@app.get("/api/browse-folder")
async def api_browse_folder(start: str = "") -> JSONResponse:
    """Open a native folder picker dialog and return the selected path."""
    if IS_VERCEL:
        return JSONResponse({"path": ""}, status_code=404)

    import platform
    import subprocess

    initial = start if start and Path(start).is_dir() else str(Path.home())

    if platform.system() == "Darwin":
        script = (
            f"set p to POSIX path of (choose folder with prompt "
            f'"Select output folder" default location POSIX file "{initial}")\n'
            f"return p"
        )
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return JSONResponse({"path": proc.stdout.strip().rstrip("/")})
        return JSONResponse({"path": ""})

    # Fallback: tkinter for Linux/Windows
    import threading

    result: dict[str, str] = {}

    def _pick() -> None:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        chosen = filedialog.askdirectory(
            initialdir=initial, title="Select output folder"
        )
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
        parallel_jobs=int(data.get("parallel_jobs", 8)),
    )


def _sse_event(data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"data: {json.dumps(data)}\n\n"


def cli() -> None:
    """CLI entry point -- start the server and open browser."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    host = "127.0.0.1"
    port = 8000
    logger.info(f"Starting CourseGrab at http://{host}:{port}")
    webbrowser.open(f"http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli()
