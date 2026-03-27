"""Tests for __main__.py entry point."""

import importlib
from unittest.mock import patch


def test_main_module_calls_cli() -> None:
    """Verify __main__.py calls cli()."""
    with patch("coursegrab.main.cli") as mock_cli:
        import coursegrab.__main__  # noqa: F401

        mock_cli.reset_mock()
        importlib.reload(coursegrab.__main__)
        mock_cli.assert_called_once()
