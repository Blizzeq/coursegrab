"""Wrapper around coursera-helper subprocess for downloading Coursera materials."""

import asyncio
import logging
import os
import re
import shlex
import shutil
import sys
import sysconfig
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COURSERA_URL_PATTERN = re.compile(r"coursera\.org/learn/(?P<slug>[a-zA-Z0-9_-]+)")


@dataclass
class DownloadOptions:
    """Options for a coursera-dl download job."""

    url: str
    output_dir: str
    cauth: str = ""
    video: bool = True
    video_resolution: str = "720p"
    subtitles: bool = True
    subtitle_languages: str = "en,pl"
    slides_pdf: bool = True
    slides_pptx: bool = True
    download_notebooks: bool = False
    download_quizzes: bool = False
    parallel_jobs: int = 8


@dataclass
class DownloadJob:
    """Tracks a running download process."""

    process: Optional[asyncio.subprocess.Process] = None
    cancelled: bool = False


def extract_slug(url: str) -> Optional[str]:
    """Extract course slug from a Coursera URL."""
    match = COURSERA_URL_PATTERN.search(url)
    return match.group("slug") if match else None


def validate_options(
    options: DownloadOptions, *, skip_output_validation: bool = False
) -> list[str]:
    """Validate download options, return list of errors."""
    errors: list[str] = []

    slug = extract_slug(options.url)
    if not slug:
        errors.append(
            "Invalid Coursera URL. Expected: coursera.org/learn/<course-slug>/..."
        )

    if not options.cauth or len(options.cauth.strip()) < 10:
        errors.append(
            "CAUTH cookie is required. Get it from your browser DevTools (Application > Cookies > coursera.org > CAUTH)."
        )

    if not skip_output_validation:
        output_path = Path(options.output_dir).expanduser()
        if not output_path.exists():
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(f"Cannot create output directory: {e}")

    if not any(
        [
            options.video,
            options.subtitles,
            options.slides_pdf,
            options.slides_pptx,
            options.download_notebooks,
            options.download_quizzes,
        ]
    ):
        errors.append("Select at least one content type to download.")

    return errors


def build_command(options: DownloadOptions) -> list[str]:
    """Build coursera-dl command from download options."""
    slug = extract_slug(options.url)
    if not slug:
        raise ValueError("Invalid Coursera URL")

    output_path = Path(options.output_dir).expanduser().resolve()

    cmd = [
        "coursera-helper",
        "-ca",
        options.cauth.strip(),
        "--path",
        str(output_path),
        "--jobs",
        str(max(1, min(options.parallel_jobs, 8))),
    ]

    if options.video:
        cmd.extend(["--video-resolution", options.video_resolution])

    if options.subtitles:
        langs = options.subtitle_languages.strip() or "en,pl"
        cmd.extend(["--subtitle-language", langs])

    if options.download_notebooks:
        cmd.append("--download-notebooks")

    if options.download_quizzes:
        cmd.append("--download-quizzes")

    # Use --ignore-formats to exclude unwanted content types (comma-separated)
    ignore_formats: list[str] = []
    if not options.video:
        ignore_formats.extend(["mp4", "m4v", "webm"])
    if not options.slides_pdf:
        ignore_formats.append("pdf")
    if not options.slides_pptx:
        ignore_formats.append("pptx")

    if ignore_formats:
        cmd.extend(["--ignore-formats", ",".join(ignore_formats)])

    cmd.append(slug)
    return cmd


def build_command_display(options: DownloadOptions) -> str:
    """Build command string for display (with masked CAUTH)."""
    cmd = build_command(options)
    # Mask the CAUTH value for security
    masked = []
    skip_next = False
    for _i, part in enumerate(cmd):
        if skip_next:
            masked.append("****")
            skip_next = False
        elif part == "-ca":
            masked.append(part)
            skip_next = True
        else:
            masked.append(part)
    return " ".join(shlex.quote(c) for c in masked)


def _find_coursera_helper() -> Optional[str]:
    """Find the coursera-helper binary across multiple locations."""
    search_dirs = [
        sysconfig.get_path("scripts"),  # venv/bin on Vercel
        os.path.dirname(sys.executable),  # alongside python binary
    ]
    for d in search_dirs:
        if not d:
            continue
        candidate = os.path.join(d, "coursera-helper")
        if os.path.isfile(candidate):
            return candidate
    # Fallback to PATH
    return shutil.which("coursera-helper")


def _build_exec_command(options: DownloadOptions) -> list[str]:
    """Build the full executable command, using binary or Python import fallback."""
    cmd = build_command(options)
    dl_path = _find_coursera_helper()

    if dl_path:
        cmd[0] = dl_path
        return cmd

    # Fallback: invoke runner.py by absolute path (not -m) so it works
    # even when cwd is changed to a writable directory on Vercel
    runner_path = str(Path(__file__).parent / "runner.py")
    args = cmd[1:]  # Everything after "coursera-helper"
    return [sys.executable, runner_path, *args]


async def run_download(
    options: DownloadOptions,
    job: DownloadJob,
    *,
    skip_output_validation: bool = False,
) -> AsyncIterator[str]:
    """Run coursera-dl and yield log lines as they appear."""
    errors = validate_options(options, skip_output_validation=skip_output_validation)
    if errors:
        for err in errors:
            yield f"ERROR: {err}"
        return

    yield f"$ {build_command_display(options)}\n"

    exec_cmd = _build_exec_command(options)
    logger.info("Executing: %s", exec_cmd[:3])

    # Set cwd to output dir so coursera-helper can write cache files
    # (Vercel Lambda CWD /var/task is read-only)
    work_dir = Path(options.output_dir).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        process = await asyncio.create_subprocess_exec(
            *exec_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(work_dir),
        )
        job.process = process

        assert process.stdout is not None
        async for line_bytes in process.stdout:
            if job.cancelled:
                process.terminate()
                yield "\n--- Download cancelled ---"
                return
            line = line_bytes.decode("utf-8", errors="replace").rstrip()
            if line:
                yield line

        return_code = await process.wait()
        if return_code == 0:
            yield "\n--- Download complete ---"
        else:
            yield f"\n--- coursera-helper exited with code {return_code} ---"

    except FileNotFoundError:
        yield "ERROR: coursera-helper not found. Install it with: pip install coursera-helper"
    except Exception as e:
        yield f"ERROR: {e}"
    finally:
        job.process = None
