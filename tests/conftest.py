"""Shared test fixtures."""

import pytest


@pytest.fixture
def valid_url() -> str:
    return "https://www.coursera.org/learn/financial-markets-global/lecture/WXzlD/the-bubble-part-2"


@pytest.fixture
def valid_course_url() -> str:
    return "https://www.coursera.org/learn/financial-markets-global"


@pytest.fixture
def fake_cauth() -> str:
    return "fake_cauth_cookie_value_for_testing_purposes_1234567890"


@pytest.fixture
def default_options(valid_url: str, fake_cauth: str, tmp_path) -> dict:
    return {
        "url": valid_url,
        "output_dir": str(tmp_path),
        "cauth": fake_cauth,
        "video": True,
        "video_resolution": "720p",
        "subtitles": True,
        "subtitle_languages": "en,pl",
        "slides_pdf": True,
        "slides_pptx": True,
        "download_notebooks": False,
        "download_quizzes": False,
    }
