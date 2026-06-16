import json
import logging
import re
import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from wild_catalog.wildlife_detection.model_download import download_file_with_progress

logger = logging.getLogger("uvicorn.error")

DEFAULT_GEOPACKAGE_BASE_URL = (
    "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest"
)
GEOPACKAGE_METADATA_URL = f"{DEFAULT_GEOPACKAGE_BASE_URL}/metadata.json"

_ARCHIVE_SUFFIX = re.compile(r"_(\d+)$")


def calculate_geopackage_urls(
    metadata: Mapping[str, object],
    base_url: str = DEFAULT_GEOPACKAGE_BASE_URL,
) -> tuple[str, ...]:
    collections = metadata["collections"]
    if not isinstance(collections, Mapping):
        raise TypeError("metadata['collections'] must be a mapping")

    urls: list[str] = []
    for collection_key, collection in collections.items():
        if not isinstance(collection, Mapping):
            raise TypeError(f"metadata['collections']['{collection_key}'] must be a mapping")

        archives = int(collection["archives"])
        for archive_index in range(archives):
            suffix = f"_{archive_index + 1}" if archives > 1 else ""
            urls.append(f"{base_url}/iNaturalist_geomodel_{collection_key}{suffix}.gpkg")

    return tuple(urls)


def import_inaturalist_open_range_data_if_missing(
    target_database_path: str | Path,
    download_dir: str | Path,
    *,
    metadata_url: str = GEOPACKAGE_METADATA_URL,
) -> int:
    target_path = Path(target_database_path)
    if target_path.exists():
        logger.info("iNaturalist open range store already exists at %s", target_path)
        return 0

    target_path.parent.mkdir(parents=True, exist_ok=True)
    download_path = Path(download_dir)
    download_path.mkdir(parents=True, exist_ok=True)

    logger.info("Importing iNaturalist open range data into %s", target_path)
    metadata = load_geopackage_metadata(metadata_url)
    geopackage_paths = [
        download_file_with_progress(url, download_path / _filename_from_url(url))
        for url in calculate_geopackage_urls(metadata)
    ]

    temporary_target_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
    _unlink_sqlite_database_files(temporary_target_path)
    try:
        rows_imported = import_geopackages(
            temporary_target_path,
            geopackage_paths,
            metadata=metadata,
        )
        temporary_target_path.replace(target_path)
        logger.info(
            "Imported %s iNaturalist open range geometries into %s",
            rows_imported,
            target_path,
        )
        return rows_imported
    finally:
        _unlink_sqlite_database_files(temporary_target_path)


def load_geopackage_metadata(metadata_url: str = GEOPACKAGE_METADATA_URL) -> Mapping[str, object]:
    with urlopen(metadata_url, timeout=60) as response:
        metadata = json.load(response)

    if not isinstance(metadata, Mapping):
        raise TypeError("GeoPackage metadata must be a mapping")

    return metadata


def create_range_store_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS range_geometries (
            id INTEGER PRIMARY KEY,
            taxon_id INTEGER NOT NULL,
            min_lon REAL NOT NULL,
            min_lat REAL NOT NULL,
            max_lon REAL NOT NULL,
            max_lat REAL NOT NULL,
            geometry_wkb BLOB NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS range_geometries_rtree USING rtree(
            id,
            min_lon,
            max_lon,
            min_lat,
            max_lat
        );

        CREATE INDEX IF NOT EXISTS idx_range_geometries_taxon_id
        ON range_geometries (taxon_id);

        CREATE TABLE IF NOT EXISTS range_store_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def geopackage_table_name(geopackage_path: str | Path) -> str:
    stem = Path(geopackage_path).stem
    if stem.startswith("iNaturalist_geomodel_"):
        return _ARCHIVE_SUFFIX.sub("", stem)

    return stem


def import_geopackages(
    target_database_path: str | Path,
    geopackage_paths: Iterable[str | Path],
    metadata: Mapping[str, object] | None = None,
) -> int:
    with closing(sqlite3.connect(target_database_path)) as connection:
        _configure_connection(connection)
        create_range_store_schema(connection)

        rows_imported = 0
        for geopackage_path in geopackage_paths:
            rows_imported += import_geopackage(connection, geopackage_path)

        _rebuild_rtree(connection)
        if metadata is not None:
            _store_metadata(connection, metadata)
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        return rows_imported


def import_geopackage(connection: sqlite3.Connection, geopackage_path: str | Path) -> int:
    before_count = _range_geometry_count(connection)
    connection.execute("ATTACH DATABASE ? AS gpkg_db", (str(geopackage_path),))
    try:
        table_name = _resolve_geopackage_table_name(connection, geopackage_path)
        rtree_table_name = f"rtree_{table_name}_geom"
        connection.execute(
            f"""
            INSERT INTO range_geometries (
                taxon_id,
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                geometry_wkb
            )
            SELECT
                CAST(d.taxon_id AS INTEGER),
                r.minx,
                r.miny,
                r.maxx,
                r.maxy,
                CASE
                    WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 0 THEN substr(d.geom, 9)
                    WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 2 THEN substr(d.geom, 41)
                    WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 4 THEN substr(d.geom, 57)
                    WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 6 THEN substr(d.geom, 57)
                    ELSE substr(d.geom, 73)
                END
            FROM gpkg_db.{_quote_identifier(table_name)} d
            JOIN gpkg_db.{_quote_identifier(rtree_table_name)} r ON d.fid = r.id
            """
        )
        connection.commit()
    finally:
        if connection.in_transaction:
            connection.rollback()
        connection.execute("DETACH DATABASE gpkg_db")

    return _range_geometry_count(connection) - before_count


def _configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA cache_size = -100000")


def _range_geometry_count(connection: sqlite3.Connection) -> int:
    return int(connection.execute("SELECT COUNT(*) FROM range_geometries").fetchone()[0])


def _rebuild_rtree(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM range_geometries_rtree")
    connection.execute(
        """
        INSERT INTO range_geometries_rtree (id, min_lon, max_lon, min_lat, max_lat)
        SELECT id, min_lon, max_lon, min_lat, max_lat
        FROM range_geometries
        """
    )


def _store_metadata(connection: sqlite3.Connection, metadata: Mapping[str, object]) -> None:
    rows = [(key, str(value)) for key, value in metadata.items() if key != "collections"]
    connection.executemany(
        """
        INSERT INTO range_store_metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        rows,
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _resolve_geopackage_table_name(
    connection: sqlite3.Connection,
    geopackage_path: str | Path,
) -> str:
    for table_name in _geopackage_table_name_candidates(geopackage_path):
        if _attached_table_exists(connection, table_name) and _attached_table_exists(
            connection,
            f"rtree_{table_name}_geom",
        ):
            return table_name

    candidates = ", ".join(_geopackage_table_name_candidates(geopackage_path))
    raise sqlite3.OperationalError(
        f"Could not find GeoPackage data and rtree tables for candidates: {candidates}"
    )


def _geopackage_table_name_candidates(geopackage_path: str | Path) -> tuple[str, ...]:
    stem = Path(geopackage_path).stem
    normalized_name = geopackage_table_name(geopackage_path)
    if stem == normalized_name:
        return (stem,)

    return (stem, normalized_name)


def _attached_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            """
            SELECT 1
            FROM gpkg_db.sqlite_master
            WHERE type = 'table'
            AND name = ?
            """,
            (table_name,),
        ).fetchone()
        is not None
    )


def _filename_from_url(url: str) -> str:
    filename = Path(urlsplit(url).path).name
    if not filename:
        raise ValueError(f"URL does not include a filename: {url}")

    return filename


def _unlink_sqlite_database_files(database_path: Path) -> None:
    database_path.unlink(missing_ok=True)
    database_path.with_name(f"{database_path.name}-wal").unlink(missing_ok=True)
    database_path.with_name(f"{database_path.name}-shm").unlink(missing_ok=True)
