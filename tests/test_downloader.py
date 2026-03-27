"""Tests for the downloader module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coursegrab.downloader import (
    DownloadJob,
    DownloadOptions,
    build_command,
    build_command_display,
    extract_slug,
    run_download,
    validate_options,
)

FAKE_CAUTH = "fake_cauth_cookie_value_for_testing_purposes_1234567890"


class TestExtractSlug:
    """Tests for extract_slug function."""

    def test_full_lecture_url(self, valid_url: str) -> None:
        assert extract_slug(valid_url) == "financial-markets-global"

    def test_course_url(self, valid_course_url: str) -> None:
        assert extract_slug(valid_course_url) == "financial-markets-global"

    def test_course_url_with_trailing_slash(self) -> None:
        url = "https://www.coursera.org/learn/machine-learning/"
        assert extract_slug(url) == "machine-learning"

    def test_invalid_url(self) -> None:
        assert extract_slug("https://google.com") is None

    def test_empty_string(self) -> None:
        assert extract_slug("") is None

    @pytest.mark.parametrize(
        "url,expected_slug",
        [
            ("https://www.coursera.org/learn/python-data", "python-data"),
            (
                "https://coursera.org/learn/deep-learning-specialization",
                "deep-learning-specialization",
            ),
            ("https://www.coursera.org/learn/ml_101/lecture/abc/intro", "ml_101"),
        ],
    )
    def test_various_urls(self, url: str, expected_slug: str) -> None:
        assert extract_slug(url) == expected_slug


class TestValidateOptions:
    """Tests for validate_options function."""

    def test_valid_options(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        errors = validate_options(opts)
        assert errors == []

    def test_invalid_url(self, tmp_path) -> None:
        opts = DownloadOptions(
            url="https://google.com", output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        errors = validate_options(opts)
        assert any("Invalid Coursera URL" in e for e in errors)

    def test_missing_cauth(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(url=valid_url, output_dir=str(tmp_path), cauth="")
        errors = validate_options(opts)
        assert any("CAUTH" in e for e in errors)

    def test_short_cauth(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(url=valid_url, output_dir=str(tmp_path), cauth="short")
        errors = validate_options(opts)
        assert any("CAUTH" in e for e in errors)

    def test_no_content_selected(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            video=False,
            subtitles=False,
            slides_pdf=False,
            slides_pptx=False,
        )
        errors = validate_options(opts)
        assert any("Select at least one" in e for e in errors)

    def test_notebooks_only_is_valid_content(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            video=False,
            subtitles=False,
            slides_pdf=False,
            slides_pptx=False,
            download_notebooks=True,
        )
        errors = validate_options(opts)
        assert not any("Select at least one" in e for e in errors)

    def test_quizzes_only_is_valid_content(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            video=False,
            subtitles=False,
            slides_pdf=False,
            slides_pptx=False,
            download_quizzes=True,
        )
        errors = validate_options(opts)
        assert not any("Select at least one" in e for e in errors)

    def test_creates_output_dir(self, valid_url: str, tmp_path) -> None:
        new_dir = tmp_path / "new" / "nested" / "dir"
        opts = DownloadOptions(url=valid_url, output_dir=str(new_dir), cauth=FAKE_CAUTH)
        errors = validate_options(opts)
        assert errors == []
        assert new_dir.exists()


class TestBuildCommand:
    """Tests for build_command function."""

    def test_basic_command(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        cmd = build_command(opts)
        assert cmd[0] == "coursera-helper"
        assert "-ca" in cmd
        assert FAKE_CAUTH in cmd
        assert "--jobs" in cmd
        idx = cmd.index("--jobs")
        assert cmd[idx + 1] == "8"  # default (max concurrent)
        assert "financial-markets-global" == cmd[-1]

    def test_parallel_jobs_custom(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH, parallel_jobs=6
        )
        cmd = build_command(opts)
        idx = cmd.index("--jobs")
        assert cmd[idx + 1] == "6"

    def test_parallel_jobs_clamped(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH, parallel_jobs=20
        )
        cmd = build_command(opts)
        idx = cmd.index("--jobs")
        assert cmd[idx + 1] == "8"  # clamped to max 8

    def test_skip_video(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH, video=False
        )
        cmd = build_command(opts)
        assert "--ignore-formats" in cmd
        idx = cmd.index("--ignore-formats")
        ignored = cmd[idx + 1].split(",")
        assert "mp4" in ignored
        assert "--video-resolution" not in cmd

    def test_video_resolution(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            video_resolution="540p",
        )
        cmd = build_command(opts)
        idx = cmd.index("--video-resolution")
        assert cmd[idx + 1] == "540p"

    def test_output_path(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        cmd = build_command(opts)
        idx = cmd.index("--path")
        assert cmd[idx + 1] == str(tmp_path.resolve())

    def test_all_formats_no_ignore(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        cmd = build_command(opts)
        # With all content types checked, no formats should be ignored
        assert "--ignore-formats" not in cmd
        assert "-f" not in cmd
        assert "--subtitle-language" in cmd
        sl_idx = cmd.index("--subtitle-language")
        assert cmd[sl_idx + 1] == "en,pl"

    def test_ignore_pptx_only(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            subtitles=False,
            slides_pptx=False,
        )
        cmd = build_command(opts)
        idx = cmd.index("--ignore-formats")
        ignored = cmd[idx + 1].split(",")
        assert "pptx" in ignored
        assert "pdf" not in ignored

    def test_ignore_all_slides(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            video=False,
            slides_pdf=False,
            slides_pptx=False,
        )
        cmd = build_command(opts)
        idx = cmd.index("--ignore-formats")
        ignored = cmd[idx + 1].split(",")
        assert "mp4" in ignored
        assert "pdf" in ignored
        assert "pptx" in ignored

    def test_invalid_url_raises(self, tmp_path) -> None:
        opts = DownloadOptions(
            url="bad-url", output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        with pytest.raises(ValueError):
            build_command(opts)

    def test_download_notebooks_flag(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            download_notebooks=True,
        )
        cmd = build_command(opts)
        assert "--download-notebooks" in cmd

    def test_download_quizzes_flag(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            download_quizzes=True,
        )
        cmd = build_command(opts)
        assert "--download-quizzes" in cmd

    def test_subtitle_language_custom(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url,
            output_dir=str(tmp_path),
            cauth=FAKE_CAUTH,
            subtitle_languages="en,de,fr",
        )
        cmd = build_command(opts)
        sl_idx = cmd.index("--subtitle-language")
        assert cmd[sl_idx + 1] == "en,de,fr"

    def test_no_subtitles_no_subtitle_flag(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH, subtitles=False
        )
        cmd = build_command(opts)
        assert "--subtitle-language" not in cmd

    def test_display_masks_cauth(self, valid_url: str, tmp_path) -> None:
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        display = build_command_display(opts)
        assert FAKE_CAUTH not in display
        assert "****" in display


class TestValidateOptionsEdgeCases:
    """Edge case tests for validate_options."""

    def test_mkdir_oserror(self, valid_url: str) -> None:
        with patch("coursegrab.downloader.Path.expanduser") as mock_expand:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path.mkdir.side_effect = OSError("Permission denied")
            mock_expand.return_value = mock_path
            opts = DownloadOptions(
                url=valid_url, output_dir="/no/access", cauth=FAKE_CAUTH
            )
            errors = validate_options(opts)
            assert any("Cannot create output directory" in e for e in errors)


class TestRunDownload:
    """Tests for run_download async generator."""

    @pytest.mark.anyio
    async def test_validation_errors_yielded(self, tmp_path) -> None:
        """run_download yields ERROR lines when validation fails."""
        opts = DownloadOptions(
            url="bad-url", output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()
        lines = [line async for line in run_download(opts, job)]
        assert any("ERROR:" in line for line in lines)

    @pytest.mark.anyio
    async def test_coursera_helper_not_found(self, valid_url: str, tmp_path) -> None:
        """run_download yields error when coursera-helper is completely unavailable."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()
        with (
            patch(
                "coursegrab.downloader._find_coursera_helper",
                return_value=None,
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError,
            ),
        ):
            lines = [line async for line in run_download(opts, job)]
        assert any("coursera-helper not found" in line for line in lines)

    @pytest.mark.anyio
    async def test_successful_download(self, valid_url: str, tmp_path) -> None:
        """run_download streams subprocess output and reports success."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()

        # Mock subprocess
        mock_stdout = AsyncMock()
        mock_stdout.__aiter__ = lambda self: self
        mock_stdout.__anext__ = AsyncMock(
            side_effect=[
                b"Downloading course...\n",
                b"Progress 50%\n",
                StopAsyncIteration,
            ]
        )

        mock_process = AsyncMock()
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock(return_value=0)

        with (
            patch(
                "coursegrab.downloader.shutil.which",
                return_value="/usr/bin/coursera-helper",
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                return_value=mock_process,
            ),
        ):
            lines = [line async for line in run_download(opts, job)]

        assert any("$" in line for line in lines)  # command display line
        assert any("Downloading course" in line for line in lines)
        assert any("Download complete" in line for line in lines)

    @pytest.mark.anyio
    async def test_download_nonzero_exit(self, valid_url: str, tmp_path) -> None:
        """run_download reports nonzero exit code."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()

        mock_stdout = AsyncMock()
        mock_stdout.__aiter__ = lambda self: self
        mock_stdout.__anext__ = AsyncMock(side_effect=StopAsyncIteration)

        mock_process = AsyncMock()
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock(return_value=1)

        with (
            patch(
                "coursegrab.downloader.shutil.which",
                return_value="/usr/bin/coursera-helper",
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                return_value=mock_process,
            ),
        ):
            lines = [line async for line in run_download(opts, job)]

        assert any("exited with code 1" in line for line in lines)

    @pytest.mark.anyio
    async def test_download_cancelled(self, valid_url: str, tmp_path) -> None:
        """run_download handles cancellation."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()
        job.cancelled = True

        mock_stdout = AsyncMock()
        mock_stdout.__aiter__ = lambda self: self
        mock_stdout.__anext__ = AsyncMock(
            side_effect=[
                b"Starting...\n",
                StopAsyncIteration,
            ]
        )

        mock_process = AsyncMock()
        mock_process.stdout = mock_stdout
        mock_process.wait = AsyncMock(return_value=0)

        with (
            patch(
                "coursegrab.downloader.shutil.which",
                return_value="/usr/bin/coursera-helper",
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                return_value=mock_process,
            ),
        ):
            lines = [line async for line in run_download(opts, job)]

        assert any("cancelled" in line for line in lines)

    @pytest.mark.anyio
    async def test_download_file_not_found_exception(
        self, valid_url: str, tmp_path
    ) -> None:
        """run_download handles FileNotFoundError from subprocess."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()

        with (
            patch(
                "coursegrab.downloader.shutil.which",
                return_value="/usr/bin/coursera-helper",
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError,
            ),
        ):
            lines = [line async for line in run_download(opts, job)]

        assert any("coursera-helper not found" in line for line in lines)

    @pytest.mark.anyio
    async def test_download_generic_exception(self, valid_url: str, tmp_path) -> None:
        """run_download handles unexpected exceptions."""
        opts = DownloadOptions(
            url=valid_url, output_dir=str(tmp_path), cauth=FAKE_CAUTH
        )
        job = DownloadJob()

        with (
            patch(
                "coursegrab.downloader.shutil.which",
                return_value="/usr/bin/coursera-helper",
            ),
            patch(
                "coursegrab.downloader.asyncio.create_subprocess_exec",
                side_effect=RuntimeError("boom"),
            ),
        ):
            lines = [line async for line in run_download(opts, job)]

        assert any("ERROR: boom" in line for line in lines)
