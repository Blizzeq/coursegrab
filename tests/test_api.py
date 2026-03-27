"""Tests for the FastAPI application."""

import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from coursegrab.main import _parse_options, _sse_event, app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_index(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "CourseGrab" in response.text


@pytest.mark.anyio
async def test_default_output(client: AsyncClient) -> None:
    response = await client.get("/api/default-output")
    assert response.status_code == 200
    data = response.json()
    assert "path" in data
    assert "coursera" in data["path"]


@pytest.mark.anyio
async def test_validate_valid_url(client: AsyncClient, default_options: dict) -> None:
    response = await client.post("/api/validate", json=default_options)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["slug"] == "financial-markets-global"


@pytest.mark.anyio
async def test_validate_invalid_url(client: AsyncClient, default_options: dict) -> None:
    default_options["url"] = "https://google.com"
    response = await client.post("/api/validate", json=default_options)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert len(data["errors"]) > 0


@pytest.mark.anyio
async def test_cancel_nonexistent_job(client: AsyncClient) -> None:
    response = await client.post("/api/cancel/99999")
    assert response.status_code == 404
    data = response.json()
    assert data["ok"] is False


@pytest.mark.anyio
async def test_download_streams_sse(client: AsyncClient, default_options: dict) -> None:
    """Test that /api/download returns SSE events."""

    async def fake_run_download(opts, job, **kwargs):
        yield "INFO: Starting download"
        yield "INFO: Done"

    with patch("coursegrab.main.run_download", side_effect=fake_run_download):
        response = await client.post("/api/download", json=default_options)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "started" in text
    assert "done" in text


@pytest.mark.anyio
async def test_cancel_existing_job(client: AsyncClient, default_options: dict) -> None:
    """Test cancelling an active download job."""
    from coursegrab.main import DownloadJob, _jobs

    # Manually insert a fake job
    job = DownloadJob()
    _jobs[42] = job

    response = await client.post("/api/cancel/42")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert job.cancelled is True

    # Cleanup
    _jobs.pop(42, None)


def test_parse_options_minimal() -> None:
    """Test _parse_options with minimal data fills defaults."""
    data = {"url": "https://coursera.org/learn/test"}
    opts = _parse_options(data)
    assert opts.url == "https://coursera.org/learn/test"
    assert opts.video is True
    assert opts.video_resolution == "720p"
    assert "coursera" in opts.output_dir


def test_parse_options_full(default_options: dict) -> None:
    """Test _parse_options with all fields."""
    opts = _parse_options(default_options)
    assert opts.video_resolution == "720p"
    assert opts.slides_pdf is True


def test_sse_event_format() -> None:
    """Test SSE event formatting."""
    result = _sse_event({"type": "log", "message": "hello"})
    assert result.startswith("data: ")
    assert result.endswith("\n\n")
    parsed = json.loads(result.removeprefix("data: ").strip())
    assert parsed["type"] == "log"
    assert parsed["message"] == "hello"
