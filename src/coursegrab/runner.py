"""Wrapper to invoke coursera-helper with Python 3.12+ compatibility.

On Python 3.12+ distutils was removed from stdlib. coursera-helper
imports it at module level. setuptools provides a shim, but on Vercel
the .pth activation hook is not processed because packages live in a
vendor directory. This module activates the shim manually before
handing off to the real entry point.
"""

import sys

# Activate setuptools distutils shim before any other import
try:
    import _distutils_hack

    _distutils_hack.ensure_local_distutils()
except Exception:
    # If setuptools is too old or not installed, try direct injection
    try:
        import importlib

        distutils = importlib.import_module("setuptools._distutils")
        sys.modules.setdefault("distutils", distutils)
        sys.modules.setdefault(
            "distutils.version",
            importlib.import_module("setuptools._distutils.version"),
        )
    except Exception:
        pass  # Last resort: hope distutils exists natively

from coursera_helper.coursera_dl import main

if __name__ == "__main__":
    main()
