import sqlite3
from contextlib import closing

import pytest

from wild_catalog.range_data import (
    calculate_geopackage_urls,
    create_range_store_schema,
    geopackage_table_name,
    import_geopackage,
    import_geopackages,
    import_inaturalist_open_range_data_if_missing,
)
from wild_catalog.range_data import (
    inaturalist_open_range_importer as range_importer,
)


def test_calculate_geopackage_urls_uses_archive_suffix_only_for_split_collections() -> None:
    metadata = {
        "version": "2.31",
        "ranges": 118632,
        "collections": {
            "OtherAnimalia": {"ranges": 4462, "archives": 1},
            "Aves": {"ranges": 6822, "archives": 2},
        },
    }

    urls = calculate_geopackage_urls(metadata, base_url="https://example.test/ranges")

    assert urls == (
        "https://example.test/ranges/iNaturalist_geomodel_OtherAnimalia.gpkg",
        "https://example.test/ranges/iNaturalist_geomodel_Aves_1.gpkg",
        "https://example.test/ranges/iNaturalist_geomodel_Aves_2.gpkg",
    )


def test_calculate_geopackage_urls_rejects_missing_collections() -> None:
    with pytest.raises(KeyError):
        calculate_geopackage_urls({})


def test_calculate_geopackage_urls_rejects_non_mapping_collections() -> None:
    with pytest.raises(TypeError, match="collections"):
        calculate_geopackage_urls({"collections": []})


def test_calculate_geopackage_urls_rejects_non_mapping_collection() -> None:
    with pytest.raises(TypeError, match="Aves"):
        calculate_geopackage_urls({"collections": {"Aves": []}})


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("iNaturalist_geomodel_Amphibia.gpkg", "iNaturalist_geomodel_Amphibia"),
        ("iNaturalist_geomodel_Aves_1.gpkg", "iNaturalist_geomodel_Aves"),
        ("custom_ranges_1.gpkg", "custom_ranges_1"),
    ],
)
def test_geopackage_table_name(filename: str, expected: str) -> None:
    assert geopackage_table_name(filename) == expected


def test_import_geopackage_migrates_rows_and_trims_geopackage_geometry_header(tmp_path) -> None:
    geopackage_path = tmp_path / "iNaturalist_geomodel_Amphibia.gpkg"
    target_connection = sqlite3.connect(":memory:")
    create_range_store_schema(target_connection)
    _create_fake_geopackage(
        geopackage_path,
        table_name="iNaturalist_geomodel_Amphibia",
        taxon_id="12345",
        wkb=b"wkb-payload",
        bounds=(-97.2, -96.8, 32.6, 33.1),
    )

    rows_imported = import_geopackage(target_connection, geopackage_path)

    assert rows_imported == 1
    imported = target_connection.execute(
        """
        SELECT taxon_id, min_lon, min_lat, max_lon, max_lat, geometry_wkb
        FROM range_geometries
        """
    ).fetchone()
    imported_taxa = target_connection.execute(
        "SELECT taxon_id, name FROM range_taxa"
    ).fetchall()
    assert imported == (12345, -97.2, 32.6, -96.8, 33.1, b"wkb-payload")
    assert imported_taxa == [(12345, "Agelaius phoeniceus")]
    target_connection.close()


def test_import_geopackage_supports_split_archive_table_name_with_suffix(tmp_path) -> None:
    geopackage_path = tmp_path / "iNaturalist_geomodel_Aves_1.gpkg"
    target_connection = sqlite3.connect(":memory:")
    create_range_store_schema(target_connection)
    _create_fake_geopackage(
        geopackage_path,
        table_name="iNaturalist_geomodel_Aves_1",
        taxon_id="67890",
        wkb=b"bird-wkb-payload",
        bounds=(-100.0, -99.0, 30.0, 31.0),
    )

    rows_imported = import_geopackage(target_connection, geopackage_path)

    assert rows_imported == 1
    imported = target_connection.execute(
        """
        SELECT taxon_id, min_lon, min_lat, max_lon, max_lat, geometry_wkb
        FROM range_geometries
        """
    ).fetchone()
    imported_taxa = target_connection.execute(
        "SELECT taxon_id, name FROM range_taxa"
    ).fetchall()
    assert imported == (67890, -100.0, 30.0, -99.0, 31.0, b"bird-wkb-payload")
    assert imported_taxa == [(67890, "Agelaius phoeniceus")]
    target_connection.close()


def test_import_geopackages_creates_store_rebuilds_rtree_and_stores_metadata(tmp_path) -> None:
    geopackage_path = tmp_path / "iNaturalist_geomodel_Amphibia.gpkg"
    target_database_path = tmp_path / "range-store.sqlite"
    _create_fake_geopackage(
        geopackage_path,
        table_name="iNaturalist_geomodel_Amphibia",
        taxon_id="12345",
        wkb=b"wkb-payload",
        bounds=(-97.2, -96.8, 32.6, 33.1),
    )

    rows_imported = import_geopackages(
        target_database_path,
        [geopackage_path],
        metadata={"version": "2.31", "ranges": 1, "collections": {"Amphibia": {"archives": 1}}},
    )

    assert rows_imported == 1
    with closing(sqlite3.connect(target_database_path)) as connection:
        range_rows = connection.execute(
            "SELECT id, taxon_id, min_lon, max_lon, min_lat, max_lat FROM range_geometries"
        ).fetchall()
        rtree_rows = connection.execute(
            "SELECT id, min_lon, max_lon, min_lat, max_lat FROM range_geometries_rtree"
        ).fetchall()
        metadata_rows = dict(connection.execute("SELECT key, value FROM range_store_metadata"))
        taxon_rows = connection.execute("SELECT taxon_id, name FROM range_taxa").fetchall()

    assert range_rows == [(1, 12345, -97.2, -96.8, 32.6, 33.1)]
    assert rtree_rows == [pytest.approx((1, -97.2, -96.8, 32.6, 33.1))]
    assert metadata_rows == {"ranges": "1", "version": "2.31"}
    assert taxon_rows == [(12345, "Agelaius phoeniceus")]


def test_import_inaturalist_open_range_data_backfills_taxa_for_existing_database(
    tmp_path,
) -> None:
    target_database_path = tmp_path / "range-store.sqlite"
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    geopackage_path = download_dir / "iNaturalist_geomodel_Amphibia.gpkg"
    _create_fake_geopackage(
        geopackage_path,
        table_name="iNaturalist_geomodel_Amphibia",
        taxon_id="12345",
        wkb=b"wkb-payload",
        bounds=(-97.2, -96.8, 32.6, 33.1),
    )

    with closing(sqlite3.connect(target_database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE range_geometries (
                    id INTEGER PRIMARY KEY,
                    taxon_id INTEGER NOT NULL,
                    min_lon REAL NOT NULL,
                    min_lat REAL NOT NULL,
                    max_lon REAL NOT NULL,
                    max_lat REAL NOT NULL,
                    geometry_wkb BLOB NOT NULL
                )
                """
            )

    rows_imported = import_inaturalist_open_range_data_if_missing(
        target_database_path,
        download_dir,
    )

    assert rows_imported == 0
    with closing(sqlite3.connect(target_database_path)) as connection:
        taxon_rows = connection.execute("SELECT taxon_id, name FROM range_taxa").fetchall()
    assert taxon_rows == [(12345, "Agelaius phoeniceus")]


def test_import_inaturalist_open_range_data_skips_when_database_exists(
    monkeypatch,
    tmp_path,
) -> None:
    target_database_path = tmp_path / "range-store.sqlite"
    target_database_path.touch()
    calls = []

    monkeypatch.setattr(
        range_importer,
        "load_geopackage_metadata",
        lambda *args, **kwargs: calls.append("metadata"),
    )

    rows_imported = import_inaturalist_open_range_data_if_missing(
        target_database_path,
        tmp_path / "downloads",
    )

    assert rows_imported == 0
    assert calls == []


def test_import_inaturalist_open_range_data_downloads_and_imports_missing_database(
    monkeypatch,
    tmp_path,
) -> None:
    target_database_path = tmp_path / "range-store.sqlite"
    download_dir = tmp_path / "downloads"
    metadata = {
        "version": "2.31",
        "ranges": 1,
        "collections": {"Aves": {"ranges": 1, "archives": 2}},
    }
    downloaded: list[tuple[str, str]] = []
    imported = []

    monkeypatch.setattr(
        range_importer,
        "load_geopackage_metadata",
        lambda metadata_url: metadata,
    )

    def fake_download(url, destination):
        downloaded.append((url, str(destination)))
        destination.write_bytes(b"geopackage")
        return destination

    def fake_import(target_path, geopackage_paths, *, metadata):
        imported.append((target_path, tuple(geopackage_paths), metadata))
        target_path.write_bytes(b"sqlite")
        return 2

    monkeypatch.setattr(range_importer, "download_file_with_progress", fake_download)
    monkeypatch.setattr(range_importer, "import_geopackages", fake_import)

    rows_imported = import_inaturalist_open_range_data_if_missing(
        target_database_path,
        download_dir,
        metadata_url="https://example.test/metadata.json",
    )

    assert rows_imported == 2
    assert target_database_path.read_bytes() == b"sqlite"
    assert downloaded == [
        (
            "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/"
            "geopackages/latest/iNaturalist_geomodel_Aves_1.gpkg",
            str(download_dir / "iNaturalist_geomodel_Aves_1.gpkg"),
        ),
        (
            "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/"
            "geopackages/latest/iNaturalist_geomodel_Aves_2.gpkg",
            str(download_dir / "iNaturalist_geomodel_Aves_2.gpkg"),
        ),
    ]
    assert imported == [
        (
            target_database_path.with_suffix(".sqlite.tmp"),
            (
                download_dir / "iNaturalist_geomodel_Aves_1.gpkg",
                download_dir / "iNaturalist_geomodel_Aves_2.gpkg",
            ),
            metadata,
        )
    ]


def test_import_geopackage_detaches_database_after_failure(tmp_path) -> None:
    geopackage_path = tmp_path / "iNaturalist_geomodel_Amphibia.gpkg"
    connection = sqlite3.connect(":memory:")
    create_range_store_schema(connection)
    with closing(sqlite3.connect(geopackage_path)) as geopackage_connection:
        with geopackage_connection:
            geopackage_connection.execute(
                """
                CREATE TABLE "iNaturalist_geomodel_Amphibia" (
                    fid INTEGER PRIMARY KEY,
                    taxon_id TEXT NOT NULL,
                    geom BLOB NOT NULL
                )
                """
            )

    with pytest.raises(sqlite3.OperationalError):
        import_geopackage(connection, geopackage_path)

    connection.execute("ATTACH DATABASE ? AS gpkg_db", (str(geopackage_path),))
    connection.execute("DETACH DATABASE gpkg_db")
    connection.close()


def test_create_range_store_schema_creates_expected_tables() -> None:
    connection = sqlite3.connect(":memory:")

    create_range_store_schema(connection)

    tables = {
        row[0]
        for row in connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'virtual table')
            """
        )
    }
    assert "range_geometries" in tables
    assert "range_geometries_rtree" in tables
    assert "range_store_metadata" in tables
    assert "range_taxa" in tables
    connection.close()


def _create_fake_geopackage(
    geopackage_path,
    table_name: str,
    taxon_id: str,
    wkb: bytes,
    bounds: tuple[float, float, float, float],
) -> None:
    minx, maxx, miny, maxy = bounds
    geometry_with_header = b"abcAefgh" + wkb
    with closing(sqlite3.connect(geopackage_path)) as connection:
        with connection:
            connection.execute(
                f"""
                CREATE TABLE "{table_name}" (
                    fid INTEGER PRIMARY KEY,
                    taxon_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    geom BLOB NOT NULL
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE "rtree_{table_name}_geom" (
                    id INTEGER PRIMARY KEY,
                    minx REAL NOT NULL,
                    maxx REAL NOT NULL,
                    miny REAL NOT NULL,
                    maxy REAL NOT NULL
                )
                """
            )
            connection.execute(
                f'INSERT INTO "{table_name}" (fid, taxon_id, name, geom) '
                "VALUES (?, ?, ?, ?)",
                (1, taxon_id, "Agelaius phoeniceus", geometry_with_header),
            )
            connection.execute(
                f'INSERT INTO "rtree_{table_name}_geom" (id, minx, maxx, miny, maxy) '
                "VALUES (?, ?, ?, ?, ?)",
                (1, minx, maxx, miny, maxy),
            )
