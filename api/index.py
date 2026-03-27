"""Vercel serverless entry point for CourseGrab."""

import sys
from pathlib import Path

# Add src/ to the Python path so coursegrab package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coursegrab.main import app  # noqa: E402
