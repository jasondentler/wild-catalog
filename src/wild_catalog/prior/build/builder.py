import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from time import monotonic

from wild_catalog.core.config import Settings
from wild_catalog.prior.build.downloader import download_bytes, download_range_map_archive
from wild_catalog.prior.build.geopackage import iter_range_geometries
from wild_catalog.prior.build.metadata import RangeMapArchive, parse_range_map_metadata
from wild_catalog.prior.build.sqlite_writer import create_range_store
from wild_catalog.prior.build.validate import validate_range_store

logger = logging.getLogger(__name__)


DEFAULT_PROGRESS_LOG_INTERVAL_SECONDS = 30.0


def build_inat21_range_map_store(
    settings: Settings,
    *,
    progress_log_interval_seconds: float = DEFAULT_PROGRESS_LOG_INTERVAL_SECONDS,
) -> Path:
    if settings.range_map_store_path is None:
        raise ValueError("WILD_CATALOG_RANGE_MAP_STORE_PATH must be configured.")

    logger.info(
        "Downloading iNat range-map metadata from %s for db=%s",
        settings.inat_range_maps_metadata_url,
        settings.range_map_store_path,
    )
    metadata_payload = download_bytes(settings.inat_range_maps_metadata_url)
    metadata = parse_range_map_metadata(metadata_payload)
    logger.info(
        "Discovered %s iNat range-map archive(s) for %s range(s), version %s, db=%s",
        len(metadata.archives),
        metadata.ranges,
        metadata.version,
        settings.range_map_store_path,
    )
    archive_paths = _download_range_map_archives(
        settings=settings,
        archives=metadata.archives,
    )

    logger.info(
        "Writing SQLite geometry/RTree range store to db=%s",
        settings.range_map_store_path,
    )
    inserted_geometry_count = create_range_store(
        settings.range_map_store_path,
        geometries=_iter_all_range_geometries(
            settings=settings,
            archive_count=len(metadata.archives),
            archives=metadata.archives,
            archive_paths=archive_paths,
            total_range_count=metadata.ranges,
            progress_log_interval_seconds=progress_log_interval_seconds,
        ),
        source="inat21-open-range-maps",
        source_version=metadata.version,
    )
    logger.info(
        "Wrote %s range geometries to db=%s",
        inserted_geometry_count,
        settings.range_map_store_path,
    )
    logger.info("Validating SQLite range store at db=%s", settings.range_map_store_path)
    validate_range_store(settings.range_map_store_path)
    logger.info("Built iNat range-map SQLite store at db=%s", settings.range_map_store_path)

    return settings.range_map_store_path


def _download_range_map_archives(
    *,
    settings: Settings,
    archives: Iterable[RangeMapArchive],
) -> dict[RangeMapArchive, Path]:
    archive_list = list(archives)

    if settings.inat_range_maps_download_concurrency <= 0:
        raise ValueError("WILD_CATALOG_INAT_RANGE_MAPS_DOWNLOAD_CONCURRENCY must be positive.")

    if not archive_list:
        return {}

    max_workers = min(
        settings.inat_range_maps_download_concurrency,
        len(archive_list),
    )
    logger.info(
        "Downloading %s range-map archive(s) with %s worker(s), db=%s",
        len(archive_list),
        max_workers,
        settings.range_map_store_path,
    )

    archive_paths: dict[RangeMapArchive, Path] = {}
    started_at = monotonic()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                download_range_map_archive,
                archive,
                download_dir=settings.inat_range_maps_download_dir,
            ): archive
            for archive in archive_list
        }

        for completed_count, future in enumerate(as_completed(futures), start=1):
            archive = futures[future]
            archive_paths[archive] = future.result()
            logger.info(
                "Downloaded/reused range-map archive %s/%s: %s; %s; db=%s",
                completed_count,
                len(archive_list),
                archive.filename,
                _format_count_progress(
                    processed_count=completed_count,
                    total_count=len(archive_list),
                    elapsed_seconds=monotonic() - started_at,
                    item_name="archives",
                ),
                settings.range_map_store_path,
            )

    return archive_paths


def _iter_all_range_geometries(
    *,
    settings: Settings,
    archive_count: int,
    archives: Iterable[RangeMapArchive],
    archive_paths: dict[RangeMapArchive, Path],
    total_range_count: int,
    progress_log_interval_seconds: float,
) -> Iterable[tuple[int, object]]:
    total_geometry_count = 0
    started_at = monotonic()

    for archive_number, archive in enumerate(archives, start=1):
        logger.info(
            "Processing range-map archive %s/%s: %s, db=%s",
            archive_number,
            archive_count,
            archive.filename,
            settings.range_map_store_path,
        )
        gpkg_path = archive_paths[archive]

        geometry_count = 0
        last_progress_at = monotonic()

        for range_geometry in iter_range_geometries(gpkg_path):
            geometry_count += 1
            total_geometry_count += 1
            yield range_geometry.taxon_id, range_geometry.geometry

            now = monotonic()

            if progress_log_interval_seconds <= 0 or (
                now - last_progress_at >= progress_log_interval_seconds
            ):
                logger.info(
                    "Processed %s geometries from %s; %s geometries total; %s; db=%s",
                    geometry_count,
                    archive.filename,
                    total_geometry_count,
                    _format_progress(
                        processed_count=total_geometry_count,
                        total_count=total_range_count,
                        elapsed_seconds=now - started_at,
                    ),
                    settings.range_map_store_path,
                )
                last_progress_at = now

        logger.info(
            "Finished archive %s: %s geometries, %s geometries total; %s; db=%s",
            archive.filename,
            geometry_count,
            total_geometry_count,
            _format_progress(
                processed_count=total_geometry_count,
                total_count=total_range_count,
                elapsed_seconds=monotonic() - started_at,
            ),
            settings.range_map_store_path,
        )


def _format_progress(
    *,
    processed_count: int,
    total_count: int,
    elapsed_seconds: float,
) -> str:
    if total_count <= 0:
        return f"progress unknown ({processed_count} processed), ETA unknown"

    percent_complete = min(processed_count / total_count * 100.0, 100.0)
    remaining_count = max(total_count - processed_count, 0)

    if processed_count <= 0 or elapsed_seconds <= 0:
        estimated_remaining_seconds = None
    else:
        seconds_per_item = elapsed_seconds / processed_count
        estimated_remaining_seconds = seconds_per_item * remaining_count

    return (
        f"{percent_complete:.1f}% complete "
        f"({processed_count}/{total_count} ranges), "
        f"ETA {_format_duration(estimated_remaining_seconds)}"
    )


def _format_count_progress(
    *,
    processed_count: int,
    total_count: int,
    elapsed_seconds: float,
    item_name: str,
) -> str:
    if total_count <= 0:
        return f"progress unknown ({processed_count} processed), ETA unknown"

    percent_complete = min(processed_count / total_count * 100.0, 100.0)
    remaining_count = max(total_count - processed_count, 0)

    if processed_count <= 0 or elapsed_seconds <= 0:
        estimated_remaining_seconds = None
    else:
        seconds_per_item = elapsed_seconds / processed_count
        estimated_remaining_seconds = seconds_per_item * remaining_count

    return (
        f"{percent_complete:.1f}% complete "
        f"({processed_count}/{total_count} {item_name}), "
        f"ETA {_format_duration(estimated_remaining_seconds)}"
    )


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"

    rounded_seconds = max(int(seconds), 0)
    hours, remainder = divmod(rounded_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"

    if minutes > 0:
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"
