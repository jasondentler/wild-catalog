import logging
from pathlib import Path
from urllib.request import urlopen

from wild_catalog.prior.build.metadata import RangeMapArchive

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


def download_bytes(url: str, *, timeout_seconds: int = 60) -> bytes:
    with urlopen(url, timeout=timeout_seconds) as response:
        return response.read()


def download_range_map_archive(
    archive: RangeMapArchive,
    *,
    download_dir: Path,
    timeout_seconds: int = 600,
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)

    destination = download_dir / archive.filename

    if destination.exists() and destination.stat().st_size > 0:
        logger.info("Reusing downloaded range-map archive %s", destination)
        return destination

    temporary_destination = destination.with_suffix(destination.suffix + ".tmp")

    logger.info("Downloading range-map archive %s to %s", archive.url, destination)

    with urlopen(archive.url, timeout=timeout_seconds) as response:
        with temporary_destination.open("wb") as temporary_file:
            while chunk := response.read(DOWNLOAD_CHUNK_SIZE_BYTES):
                temporary_file.write(chunk)

    temporary_destination.replace(destination)
    logger.info("Downloaded range-map archive %s", destination)

    return destination
