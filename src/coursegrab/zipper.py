"""ZIP archive creation for downloaded course files."""

import asyncio
import logging
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _create_zip_sync(source_dir: Path, zip_path: Path) -> tuple[int, int]:
    """Create ZIP synchronously. Returns (file_count, total_bytes)."""
    file_count = 0
    total_bytes = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(source_dir.rglob("*")):
            if file_path.is_file():
                arcname = str(file_path.relative_to(source_dir))
                zf.write(file_path, arcname)
                file_count += 1
                total_bytes += file_path.stat().st_size
    logger.info(f"Created ZIP: {file_count} files, {total_bytes} bytes -> {zip_path}")
    return file_count, total_bytes


async def create_zip_archive(source_dir: Path, zip_path: Path) -> tuple[int, int]:
    """Create ZIP archive asynchronously. Returns (file_count, total_bytes)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create_zip_sync, source_dir, zip_path)
